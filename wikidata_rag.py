import pandas as pd
import requests
from tqdm import tqdm
import time
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
import google.generativeai as genai
from query_engine import QueryEngine
from entity_property_retrieval import EntityPropertyRetrieval
from config import GEMINI_API_KEY
from simcse import SimCSE

class WikidataRAG:
    def __init__(self, gemini_api_key=GEMINI_API_KEY, beam_width=5, max_depth=3):
        """
        Initialize WikidataRAG with beam search parameters.
        
        Parameters:
        -----------
        gemini_api_key : str
            API key for Google's Gemini model
        beam_width : int
            Number of top paths to maintain during beam search
        max_depth : int
            Maximum depth to explore in the knowledge graph
        """
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.entity_retriever = EntityPropertyRetrieval()
        self.query_engine = QueryEngine()
        
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Initialize SimCSE model for similarity scoring
        self.model = SimCSE("princeton-nlp/sup-simcse-roberta-large")
        
    def extract_entities_from_question(self, question):
        """
        Extract potential entities from the question using Gemini.
        
        Parameters:
        -----------
        question : str
            User question
            
        Returns:
        --------
        list
            List of potential entity names
        """
        prompt = f"""
        Extract the main entities from this question that I should search for in a knowledge base:
        Question: {question}
        
        Return only the entity names as a comma-separated list, with no additional text.
        """
        
        response = self.gemini_model.generate_content(prompt)
        entity_text = response.text.strip()
        entities = [e.strip() for e in entity_text.split(',')]
        return entities
    
    def get_similarity_score(self, question, path_text):
        """
        Calculate similarity between question and a verbalized path using SimCSE.
        
        Parameters:
        -----------
        question : str
            User question
        path_text : str
            Verbalized path from knowledge graph
            
        Returns:
        --------
        float
            Similarity score
        """
        similarity = self.model.similarity(question, path_text)
        
        return similarity
    
    def verbalize_path(self, path):
        """
        Convert a path of entities and properties to natural language.
        
        Parameters:
        -----------
        path : list
            List of dictionaries representing entities and properties
            
        Returns:
        --------
        str
            Natural language representation of the path
        """
        if not path:
            return ""
        
        text_parts = []
        for i, node in enumerate(path):
            if i % 2 == 0:  # Entity
                text_parts.append(node.get('label', node.get('entity_id', '')))
            else:  # Property
                text_parts.append(node.get('label', node.get('property_id', '')))
        
        return " → ".join(text_parts)
    
    def get_entity_neighbors(self, entity_id):
        """
        Get all neighboring properties and entities for a given entity.
        
        Parameters:
        -----------
        entity_id : str
            Wikidata entity ID (Q number)
            
        Returns:
        --------
        list
            List of dictionaries containing property and target entity information
        """
        query = f"""
        SELECT ?property ?propertyLabel ?target ?targetLabel ?targetDescription
        WHERE {{
          wd:{entity_id} ?prop ?target .
          ?property wikibase:directClaim ?prop .
          
          # Get labels
          SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "en" .
          }}
          
          # Only include entities and some literals
          FILTER(STRSTARTS(STR(?target), "http://www.wikidata.org/entity/") || DATATYPE(?target) IN (xsd:dateTime, xsd:decimal, xsd:integer))
        }}
        LIMIT 100
        """
        
        results = self.query_engine.run_query(query)
        neighbors = []
        
        if not results.empty:
            for _, row in results.iterrows():
                # Extract entity ID from URI if it's an entity
                target_id = row.get('target', '')
                if 'wikidata.org/entity/' in target_id:
                    target_id = target_id.split('/')[-1]
                
                neighbors.append({
                    'property_id': row.get('property', '').split('/')[-1],
                    'property_label': row.get('propertyLabel', ''),
                    'target_id': target_id,
                    'target_label': row.get('targetLabel', ''),
                    'target_description': row.get('targetDescription', '')
                })
        
        return neighbors
    
    def beam_search(self, question):
        """
        Perform beam search to find relevant paths in the knowledge graph.
        
        Parameters:
        -----------
        question : str
            User question
            
        Returns:
        --------
        list
            Top-N paths with highest relevance scores
        """
        # Extract entities from question
        entity_names = self.extract_entities_from_question(question)
        
        print("Extracted entities:", entity_names)
        
        # Initialize beam with top-N entities from Wikidata search
        beam = []
        for name in entity_names:
            entities = self.entity_retriever.search_entities(name, limit=self.beam_width)
            for _, entity in entities.iterrows():
                path = [{
                    'entity_id': entity['entity_id'],
                    'label': entity['label'],
                    'description': entity['description']
                }]
                path_text = self.verbalize_path(path)
                score = self.get_similarity_score(question, path_text)
                beam.append({
                    'path': path,
                    'score': score,
                    'verbalized': path_text
                })
        
        # Sort and keep top-N paths
        beam = sorted(beam, key=lambda x: x['score'], reverse=True)[:self.beam_width]
        
        # Expand paths up to max depth
        for depth in range(self.max_depth):
            new_candidates = []
            
            for path_item in tqdm(beam, desc=f"Depth {depth+1}/{self.max_depth}"):
                current_path = path_item['path']
                last_entity = current_path[-1]
                
                # Get neighbors of the last entity in the path
                neighbors = self.get_entity_neighbors(last_entity['entity_id'])
                
                for neighbor in neighbors:
                    # Create new path by adding property and target entity
                    new_path = current_path.copy()
                    
                    # Add property
                    new_path.append({
                        'property_id': neighbor['property_id'],
                        'label': neighbor['property_label']
                    })
                    
                    # Add target entity
                    new_path.append({
                        'entity_id': neighbor['target_id'],
                        'label': neighbor['target_label'],
                        'description': neighbor['target_description']
                    })
                    
                    # Calculate score
                    path_text = self.verbalize_path(new_path)
                    score = self.get_similarity_score(question, path_text)
                    
                    new_candidates.append({
                        'path': new_path,
                        'score': score,
                        'verbalized': path_text
                    })
                
                # Avoid rate limiting
                time.sleep(0.1)
            
            # Combine existing beam with new candidates and keep top-N
            beam = sorted(beam + new_candidates, key=lambda x: x['score'], reverse=True)[:self.beam_width]
        
        return beam
    
    def answer_question(self, question):
        """
        Answer a question using Wikidata knowledge graph.
        
        Parameters:
        -----------
        question : str
            User question
            
        Returns:
        --------
        dict
            Answer with supporting paths
        """
        # Find relevant paths using beam search
        paths = self.beam_search(question)
        
        # Generate answer using Gemini with the top paths as context
        context = "\n\n".join([f"Path {i+1}: {path['verbalized']}" for i, path in enumerate(paths[:3])])
        
        prompt = f"""
        Question: {question}
        
        Based on the following information from a knowledge graph:
        
        {context}
        
        Please provide a concise and accurate answer to the question.
        """
        
        response = self.gemini_model.generate_content(prompt)
        
        return {
            'answer': response.text,
            'supporting_paths': [{'path': p['verbalized'], 'score': p['score']} for p in paths[:3]]
        }

# Example usage
if __name__ == "__main__":
    # Initialize WikidataRAG with your Gemini API key
    wikidata_rag = WikidataRAG()
    
    # Answer a question
    question = "Who was the director of Inception"
    result = wikidata_rag.answer_question(question)
    
    print(f"Question: {question}")
    print(f"Answer: {result['answer']}")
    print("\nSupporting paths:")
    for i, path in enumerate(result['supporting_paths']):
        print(f"{i+1}. {path['path']} (score: {path['score']:.4f})")
