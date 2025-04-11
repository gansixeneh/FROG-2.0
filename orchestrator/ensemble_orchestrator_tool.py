# orchestrator/ensemble_orchestrator_tool.py
from tools.entity_linking_tool import EntityLinkingTool
from tools.property_retrieval_tool import PropertyRetrievalTool
from tools.sparql_execution_tool import SPARQLExecutionTool
from tools.answer_generation_tool import AnswerGenerationTool
import google.generativeai as genai
from config import GEMINI_API_KEY

class EnsembleOrchestratorTool:
    def __init__(self):
        self.entity_linker = EntityLinkingTool()
        self.property_retriever = PropertyRetrievalTool()
        self.sparql_executor = SPARQLExecutionTool()
        self.answer_generator = AnswerGenerationTool()

        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate_sparql_query(self, entity_id, question, properties_json):
        """Use Gemini to create a SPARQL query from entity, question, and properties"""
        prompt = f"""
        You are a SPARQL query generator for Wikidata.

        Given:
        - Entity: {entity_id}
        - Question: {question}
        - Properties: {properties_json}

        Generate a SPARQL query that answers the question using the entity and its properties.
        Do NOT include explanations, just return the query.
        """
        response = self.model.generate_content(prompt)
        query = response.text.strip()

        # Remove markdown formatting if Gemini wrapped it in triple backticks
        if query.startswith("```"):
            query = query.strip("`").strip()
            if query.startswith("sparql"):
                query = query[len("sparql"):].strip()

        return query

    def run(self, question: str):
        print("\n🔍 Linking entities...")
        entities = self.entity_linker._run(question)
        if not entities:
            return "❌ Could not find any linked entities."

        # Use the first linked entity
        target = entities[0]
        entity_id = target["wikidata_id"]
        print(f"✅ Linked to: {target['label']} ({entity_id})")

        print("\n📦 Retrieving properties...")
        props_json = self.property_retriever._run(entity_id)

        print("\n🧠 Generating SPARQL query...")
        sparql = self.generate_sparql_query(entity_id, question, props_json)
        print(f"📄 SPARQL query:\n{sparql}")

        print("\n🚀 Executing query...")
        result = self.sparql_executor._run(sparql)

        if "SPARQL Error" in result or "No results" in result:
            return "⚠️ Could not get an answer from Wikidata."

        print("\n💬 Generating final answer...")
        answer = self.answer_generator._run(result)

        return {
            "answer": answer,
            "entity": target["label"],
            "wikidata_id": entity_id,
            "sparql": sparql,
            "raw_result": result
        }
