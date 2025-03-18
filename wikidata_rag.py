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
        if not path:
            return ""

        temp_path = path.copy()
        if len(temp_path) % 2 == 0:
            temp_path.append({"label": "Unknown entity"})

        if len(temp_path) == 1:
            entity = temp_path[0]
            label = entity.get("label") or entity.get("entity_id", "")
            return (
                f"{label} ({entity.get('description')})"
                if entity.get("description")
                else label
            )

        sentences = []

        for i in range(1, len(temp_path), 2):
            if i + 1 >= len(temp_path):
                break
            prop_node = temp_path[i]
            prev_entity = temp_path[i - 1]
            next_entity = temp_path[i + 1]

            def format_entity(entity):
                text = entity.get("label") or entity.get("entity_id", "")
                return (
                    f"{text} ({entity.get('description')})"
                    if entity.get("description")
                    else text
                )

            prop_label = prop_node.get("label") or prop_node.get("property_id", "")
            direction = prop_node.get("direction", "tail")
            if direction == "tail":
                sentence = f"{format_entity(prev_entity)} has relation {prop_label} with {format_entity(next_entity)}"
            else:

                sentence = f"{format_entity(next_entity)} has relation {prop_label} with {format_entity(prev_entity)}"
            sentences.append(sentence)

        # return ". ".join(sentences)
        return sentences[-1]

    def get_entity_properties(self, entity_id):
        properties = []

        query_tail = f"""
            SELECT DISTINCT ?property ?propertyLabel
            WHERE {{
            wd:{entity_id} ?prop ?target .
            ?property wikibase:directClaim ?prop .
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
        """
        results_tail = self.query_engine.run_query(query_tail)
        if not results_tail.empty:
            for _, row in results_tail.iterrows():
                properties.append(
                    {
                        "property_id": row.get("property", "").split("/")[-1],
                        "property_label": row.get("propertyLabel", ""),
                        "direction": "tail",
                    }
                )

        query_head = f"""
            SELECT DISTINCT ?property ?propertyLabel
            WHERE {{
            ?subject ?prop wd:{entity_id} .
            ?property wikibase:directClaim ?prop .
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
        """
        results_head = self.query_engine.run_query(query_head)
        if not results_head.empty:
            for _, row in results_head.iterrows():
                properties.append(
                    {
                        "property_id": row.get("property", "").split("/")[-1],
                        "property_label": row.get("propertyLabel", ""),
                        "direction": "head",
                    }
                )
        return properties

    def get_property_targets(self, entity_id, property_id, direction, limit=10):
        if direction == "tail":
            query = f"""
                SELECT ?target ?targetLabel ?targetDescription
                WHERE {{
                wd:{entity_id} wdt:{property_id} ?target .
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
                FILTER(STRSTARTS(STR(?target), "http://www.wikidata.org/entity/") ||
                        DATATYPE(?target) IN (xsd:dateTime, xsd:decimal, xsd:integer))
                }}
            """
        else:
            query = f"""
                SELECT ?source ?sourceLabel ?sourceDescription
                WHERE {{
                ?source wdt:{property_id} wd:{entity_id} .
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
                FILTER(STRSTARTS(STR(?source), "http://www.wikidata.org/entity/") ||
                        DATATYPE(?source) IN (xsd:dateTime, xsd:decimal, xsd:integer))
                }}
            """
        results = self.query_engine.run_query(query)
        targets = []
        if not results.empty:

            if len(results) > limit:
                results = results.sample(n=limit)
            for _, row in results.iterrows():
                if direction == "tail":
                    target_id = row.get("target", "")
                    if "wikidata.org/entity/" in target_id:
                        target_id = target_id.split("/")[-1]
                    targets.append(
                        {
                            "entity_id": target_id,
                            "label": row.get("targetLabel", ""),
                            "description": row.get("targetDescription", ""),
                        }
                    )
                else:
                    source_id = row.get("source", "")
                    if "wikidata.org/entity/" in source_id:
                        source_id = source_id.split("/")[-1]
                    targets.append(
                        {
                            "entity_id": source_id,
                            "label": row.get("sourceLabel", ""),
                            "description": row.get("sourceDescription", ""),
                        }
                    )
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
            All stored beams from each depth with their relevance scores
        """
        entity_names = self.extract_entities_from_question(question)
        print("Extracted entities:", entity_names)

        beam = []
        for name in entity_names:
            entities = self.entity_retriever.search_entities(
                name, limit=self.beam_width
            )
            for _, entity in entities.iterrows():
                path = [
                    {
                        "entity_id": entity["entity_id"],
                        "label": entity["label"],
                        "description": entity["description"],
                    }
                ]
                path_text = self.verbalize_path(path)
                score = self.get_similarity_score(question, path_text)
                beam.append({"path": path, "score": score, "verbalized": path_text})

        beam = sorted(beam, key=lambda x: x["score"], reverse=True)[: self.beam_width]

        all_beams = beam[:]
        current_beam = beam[:]

        for depth in range(self.max_depth):
            new_candidates = []

            for path_item in tqdm(
                current_beam, desc=f"Depth {depth+1}/{self.max_depth}"
            ):
                current_path = path_item["path"]
                last_entity = current_path[-1]

                properties = self.get_entity_properties(last_entity["entity_id"])

                property_candidates = []
                for prop in properties:
                    temp_path = current_path.copy()
                    temp_path.append(
                        {
                            "property_id": prop["property_id"],
                            "label": prop["property_label"],
                            "direction": prop["direction"],
                        }
                    )
                    path_text = self.verbalize_path(temp_path)
                    score = self.get_similarity_score(question, path_text)
                    property_candidates.append(
                        {"property": prop, "score": score, "path": temp_path}
                    )

                top_properties = sorted(
                    property_candidates, key=lambda x: x["score"], reverse=True
                )[: self.beam_width]

                for prop_item in top_properties:
                    property_id = prop_item["property"]["property_id"]
                    direction = prop_item["property"]["direction"]
                    prop_path = prop_item["path"]

                    targets = self.get_property_targets(
                        last_entity["entity_id"],
                        property_id,
                        direction,
                        limit=10,
                    )

                    for target in targets:
                        candidate_id = target["entity_id"]
                        if any(node.get("entity_id") == candidate_id for node in prop_path):
                            continue
                        new_path = prop_path.copy()
                        new_path.append(
                            {
                                "entity_id": target["entity_id"],
                                "label": target["label"],
                                "description": target["description"],
                                "direction": direction,
                            }
                        )

                        path_text = self.verbalize_path(new_path)
                        score = self.get_similarity_score(question, path_text)

                        new_candidates.append(
                            {"path": new_path, "score": score, "verbalized": path_text}
                        )

                time.sleep(0.1)

            current_beam = sorted(
                new_candidates, key=lambda x: x["score"], reverse=True
            )[: self.beam_width]
            all_beams.extend(current_beam)

        return all_beams

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
            [f"Path {i+1}: {path['verbalized']}" for i, path in enumerate(paths)]
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
                {"path": p["verbalized"], "score": p["score"]} for p in paths
            ],
        }


if __name__ == "__main__":

    wikidata_rag = WikidataRAG()

    question = "Who was Tom Hanks married to?"
    result = wikidata_rag.answer_question(question)

    print(f"Question: {question}")
    print(f"Answer: {result['answer']}")
    print("\nSupporting paths:")
    for i, path in enumerate(result["supporting_paths"]):
        print(f"{i+1}. {path['path']} (score: {path['score']:.4f})")
