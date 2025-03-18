from tqdm import tqdm
import time
import google.generativeai as genai
from query_engine import QueryEngine
from entity_property_retrieval import EntityPropertyRetrieval
from config import GEMINI_API_KEY
from simcse import SimCSE


class WikidataRAG:
    def __init__(self, gemini_api_key=GEMINI_API_KEY, beam_width=3, max_depth=3):
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

        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")

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
        entities = [e.strip() for e in entity_text.split(",")]
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

        original_tqdm = tqdm.__init__

        def silent_tqdm_init(*args, **kwargs):
            kwargs["disable"] = True
            return original_tqdm(*args, **kwargs)

        tqdm.__init__ = silent_tqdm_init

        try:

            similarity = self.model.similarity(question, path_text)
            return similarity
        finally:

            tqdm.__init__ = original_tqdm

    def verbalize_path(self, path):
        """
        Convert a path of entities and properties to natural language,
        including descriptions where available.

        Parameters:
        -----------
        path : list
            List of dictionaries representing entities and properties

        Returns:
        --------
        str
            Natural language representation of the path with descriptions
        """
        if not path:
            return ""

        text_parts = []
        for i, node in enumerate(path):
            label = node.get(
                "label", node.get("entity_id" if i % 2 == 0 else "property_id", "")
            )
            description = node.get("description", "")

            if description:
                text_parts.append(f"{label} ({description})")
            else:
                text_parts.append(label)

        return " → ".join(text_parts)

    def get_entity_properties(self, entity_id):
        """
        Get all distinct properties for a given entity.

        Parameters:
        -----------
        entity_id : str
            Wikidata entity ID (Q number)

        Returns:
        --------
        list
            List of dictionaries containing property information
        """
        query = f"""
                 SELECT DISTINCT ?property ?propertyLabel
                 WHERE {{
                   wd:{entity_id} ?prop ?target .
                   ?property wikibase:directClaim ?prop .
                   
                   SERVICE wikibase:label {{
                     bd:serviceParam wikibase:language "en" .
                   }}
                 }}
                 """

        results = self.query_engine.run_query(query)
        properties = []

        if not results.empty:
            for _, row in results.iterrows():
                properties.append({
                    "property_id": row.get("property", "").split("/")[-1],
                    "property_label": row.get("propertyLabel", "")
                })

        return properties

    def get_property_targets(self, entity_id, property_id, limit=10):
        """
        Get target entities for a specific property of an entity.

        Parameters:
        -----------
        entity_id : str
            Wikidata entity ID (Q number)
        property_id : str
            Wikidata property ID (P number)
        limit : int
            Maximum number of targets to return (randomly selected if more exist)

        Returns:
        --------
        list
            List of dictionaries containing target entity information
        """
        query = f"""
                 SELECT ?target ?targetLabel ?targetDescription
                 WHERE {{
                   wd:{entity_id} wdt:{property_id} ?target .
                   
                   SERVICE wikibase:label {{
                     bd:serviceParam wikibase:language "en" .
                   }}
                   
                   FILTER(STRSTARTS(STR(?target), "http://www.wikidata.org/entity/") || DATATYPE(?target) IN (xsd:dateTime, xsd:decimal, xsd:integer))
                 }}
                 """

        results = self.query_engine.run_query(query)
        targets = []

        if not results.empty:
            # Randomly sample if more than limit
            if len(results) > limit:
                results = results.sample(n=limit)
                
            for _, row in results.iterrows():
                target_id = row.get("target", "")
                if "wikidata.org/entity/" in target_id:
                    target_id = target_id.split("/")[-1]

                targets.append({
                    "target_id": target_id,
                    "target_label": row.get("targetLabel", ""),
                    "target_description": row.get("targetDescription", "")
                })

        return targets

    def beam_search(self, question):
        """
        Perform beam search to find relevant paths in the knowledge graph.
        First retrieves properties, ranks them, then explores targets for top properties.

        Parameters:
        -----------
        question : str
            User question

        Returns:
        --------
        list
            Top-N paths with highest relevance scores
        """
        entity_names = self.extract_entities_from_question(question)
        print("Extracted entities:", entity_names)

        beam = []
        for name in entity_names:
            entities = self.entity_retriever.search_entities(name, limit=self.beam_width)
            for _, entity in entities.iterrows():
                path = [{
                    "entity_id": entity["entity_id"],
                    "label": entity["label"],
                    "description": entity["description"],
                }]
                path_text = self.verbalize_path(path)
                score = self.get_similarity_score(question, path_text)
                beam.append({"path": path, "score": score, "verbalized": path_text})

        beam = sorted(beam, key=lambda x: x["score"], reverse=True)[:self.beam_width]

        for depth in range(self.max_depth):
            new_candidates = []

            for path_item in tqdm(beam, desc=f"Depth {depth+1}/{self.max_depth}"):
                current_path = path_item["path"]
                last_entity = current_path[-1]
                
                # Step 1: Get all distinct properties for the entity
                properties = self.get_entity_properties(last_entity["entity_id"])
                
                # Step 2: Rank properties by evaluating them in the context of the question
                property_candidates = []
                for prop in properties:
                    temp_path = current_path.copy()
                    temp_path.append({
                        "property_id": prop["property_id"],
                        "label": prop["property_label"]
                    })
                    path_text = self.verbalize_path(temp_path)
                    score = self.get_similarity_score(question, path_text)
                    property_candidates.append({
                        "property": prop,
                        "score": score,
                        "path": temp_path
                    })
                
                # Get top properties based on relevance
                top_properties = sorted(property_candidates, key=lambda x: x["score"], reverse=True)[:self.beam_width]
                
                # Step 3: For each top property, explore up to 10 target entities
                for prop_item in top_properties:
                    property_id = prop_item["property"]["property_id"]
                    prop_path = prop_item["path"]
                    
                    targets = self.get_property_targets(
                        last_entity["entity_id"], 
                        property_id, 
                        limit=10
                    )
                    
                    for target in targets:
                        new_path = prop_path.copy()
                        new_path.append({
                            "entity_id": target["target_id"],
                            "label": target["target_label"],
                            "description": target["target_description"]
                        })
                        
                        path_text = self.verbalize_path(new_path)
                        score = self.get_similarity_score(question, path_text)
                        
                        new_candidates.append({
                            "path": new_path, 
                            "score": score, 
                            "verbalized": path_text
                        })
                
                time.sleep(0.1)

            beam = sorted(beam + new_candidates, key=lambda x: x["score"], reverse=True)[:self.beam_width]

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

        paths = self.beam_search(question)

        context = "\n\n".join(
            [f"Path {i+1}: {path['verbalized']}" for i, path in enumerate(paths[:3])]
        )

        prompt = f"""
		          Question: {question}
		          
		          Based on the following information from a knowledge graph:
		          
		          {context}
		          
		          Please provide a concise and accurate answer to the question.
		          """

        response = self.gemini_model.generate_content(prompt)

        return {
            "answer": response.text,
            "supporting_paths": [
                {"path": p["verbalized"], "score": p["score"]} for p in paths[:3]
            ],
        }


if __name__ == "__main__":

    wikidata_rag = WikidataRAG()

    question = "Who was the director of Inception"
    result = wikidata_rag.answer_question(question)

    print(f"Question: {question}")
    print(f"Answer: {result['answer']}")
    print("\nSupporting paths:")
    for i, path in enumerate(result["supporting_paths"]):
        print(f"{i+1}. {path['path']} (score: {path['score']:.4f})")
