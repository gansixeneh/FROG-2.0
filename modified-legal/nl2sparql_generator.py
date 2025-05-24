"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator - Modified for Fuseki Server

This version supports context-aware entity selection, generating queries with real entities from
the knowledge graph that match the template structure using a discovery-based approach.
"""

import json
import random
import re
import datetime
import csv
import io
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import Counter
from kg_schema_extractor import legal_entity_label


class SparqlExecutor:
    """A class to execute SPARQL queries against the Fuseki server."""

    def __init__(self, endpoint_url="http://localhost:3030/modified-lex2kg/query"):
        """Initialize the SPARQL executor with the Fuseki endpoint."""
        self.endpoint = SPARQLWrapper(endpoint_url)
        self.endpoint.setReturnFormat(JSON)

    def execute_query(self, query, return_format="dict"):
        # print(f"Executing SPARQL query: {query}")
        """
        Execute a SPARQL query and return results.

        Args:
            query (str): SPARQL query to execute
            return_format (str): Format to return results in ("dict", "raw", "pandas")

        Returns:
            Results in the specified format
        """
        # add rdfs prefix before query
        query = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n" + query
        self.endpoint.setQuery(query)
        results = self.endpoint.query().convert()

        if return_format == "raw":
            return results

        # Extract bindings from SPARQL JSON results
        result_list = []
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                row_dict = {}
                for var, value in binding.items():
                    if value["type"] == "uri":
                        row_dict[var] = value["value"]
                    elif value["type"] == "literal":
                        row_dict[var] = value["value"]
                    else:
                        row_dict[var] = value["value"]
                result_list.append(row_dict)

        if return_format == "pandas":
            import pandas as pd

            if result_list:
                return pd.DataFrame(result_list)
            return pd.DataFrame()

        # Default to dict format
        return result_list


class VariationGenerator:
    """Generates variations of natural language questions"""

    def generate_variations(self, question, english_question, category, count=3):
        """
        Generate variations of a question

        Args:
            question (str): Original question in Indonesian
            english_question (str): Original question in English
            category (str): Question category
            count (int): Number of variations to generate

        Returns:
            list: Array of variation dictionaries with Indonesian and English versions
        """
        variations = []

        # Add legal-specific variations
        if category == "legal":
            variations.extend(self.get_legal_variations(question, english_question))

        # Add general variations
        variations.extend(self.get_general_variations(question, english_question))

        # Ensure we don't have duplicate variations
        unique_variations = []
        seen_questions = set()

        for var in variations:
            if var["indonesian"] not in seen_questions:
                seen_questions.add(var["indonesian"])
                unique_variations.append(var)

        # Return requested number of variations (or fewer if not enough generated)
        return unique_variations[: min(count, len(unique_variations))]

    def get_legal_variations(self, question, english_question):
        """
        Get variations specific to legal document questions

        Args:
            question (str): Original question in Indonesian
            english_question (str): Original question in English

        Returns:
            list: Array of variation dictionaries
        """
        variations = []

        # "Apa judul dari" variations
        if question.startswith("Apa judul dari"):
            variations.append(
                {
                    "indonesian": question.replace("Apa judul dari", "Apa nama dari"),
                    "english": english_question.replace(
                        "What is the title of", "What is the name of"
                    ),
                }
            )
            variations.append(
                {
                    "indonesian": question.replace(
                        "Apa judul dari", "Bagaimana judul dari"
                    ),
                    "english": english_question.replace(
                        "What is the title of", "How is the title of"
                    ),
                }
            )
            variations.append(
                {
                    "indonesian": "Tolong beritahu saya " + question.lower(),
                    "english": "Please tell me " + english_question.lower(),
                }
            )

        # "Kapan" variations
        elif question.startswith("Kapan"):
            variations.append(
                {
                    "indonesian": question.replace("Kapan", "Pada tanggal berapa"),
                    "english": english_question.replace("When was", "On what date was"),
                }
            )
            variations.append(
                {
                    "indonesian": "Tanggal berapa " + question[6:],
                    "english": "What date was " + english_question[9:],
                }
            )

        # "Di mana" variations
        elif question.startswith("Di mana"):
            variations.append(
                {
                    "indonesian": question.replace("Di mana", "Di kota mana"),
                    "english": english_question.replace(
                        "Where was", "In which city was"
                    ),
                }
            )
            variations.append(
                {
                    "indonesian": question.replace("Di mana", "Di tempat mana"),
                    "english": english_question.replace(
                        "Where was", "In what place was"
                    ),
                }
            )

        # "Siapa yang" variations
        elif question.startswith("Siapa yang"):
            variations.append(
                {
                    "indonesian": question.replace(
                        "Siapa yang", "Siapa nama orang yang"
                    ),
                    "english": english_question.replace(
                        "Who", "What is the name of the person who"
                    ),
                }
            )
            variations.append(
                {
                    "indonesian": "Oleh siapa "
                    + question[10:].replace("mengesahkan", "disahkan"),
                    "english": "By whom was "
                    + english_question[4:].replace("enacted", "signed"),
                }
            )

        # "Apa jabatan" variations
        elif question.startswith("Apa jabatan"):
            variations.append(
                {
                    "indonesian": question.replace("Apa jabatan", "Apa posisi"),
                    "english": english_question.replace(
                        "What is the position", "What is the role"
                    ),
                }
            )

        # "Apa jenis peraturan" variations
        elif question.startswith("Apa jenis peraturan"):
            variations.append(
                {
                    "indonesian": question.replace(
                        "Apa jenis peraturan", "Apa kategori peraturan"
                    ),
                    "english": english_question.replace(
                        "What type of regulation", "What category of regulation"
                    ),
                }
            )
            variations.append(
                {
                    "indonesian": question.replace(
                        "Apa jenis peraturan dari", "Termasuk jenis peraturan apa"
                    ),
                    "english": english_question.replace(
                        "What type of regulation is", "Which type of regulation is"
                    ),
                }
            )

        # "Apa isi dari" variations
        elif question.startswith("Apa isi dari"):
            variations.append(
                {
                    "indonesian": question.replace("Apa isi dari", "Apa konten dari"),
                    "english": english_question.replace(
                        "What is the content of", "What is the text of"
                    ),
                }
            )
            variations.append(
                {
                    "indonesian": question.replace(
                        "Apa isi dari", "Bagaimana bunyi dari"
                    ),
                    "english": english_question.replace(
                        "What is the content of", "How does the text read for"
                    ),
                }
            )

        # "Berapa jumlah" variations
        elif question.startswith("Berapa jumlah"):
            variations.append(
                {
                    "indonesian": "Ada berapa " + question[13:],
                    "english": "How many " + english_question[13:],
                }
            )

        return variations

    def get_general_variations(self, question, english_question):
        """
        Get general variations that apply to any question

        Args:
            question (str): Original question in Indonesian
            english_question (str): Original question in English

        Returns:
            list: Array of variation dictionaries
        """
        variations = []

        # Add please
        if question.endswith("?"):
            variations.append(
                {
                    "indonesian": question.replace("?", " tolong?"),
                    "english": english_question.replace("?", " please?"),
                }
            )

        # Could you tell me...
        variations.append(
            {
                "indonesian": f"Bisakah Anda memberi tahu saya {question.lower()}",
                "english": f"Could you tell me {english_question.lower()}",
            }
        )

        # I want to know...
        variations.append(
            {
                "indonesian": f"Saya ingin mengetahui {question.lower()}",
                "english": f"I want to know {english_question.lower()}",
            }
        )

        return variations


class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for legal documents."""

    def __init__(
        self, config, endpoint_url="http://localhost:3030/modified-lex2kg/query"
    ):
        """
        Initialize the generator with knowledge graph schema information

        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
            endpoint_url (str): URL of the Fuseki SPARQL endpoint
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.variation_generator = VariationGenerator()

        # Create a SPARQL executor to connect to Fuseki
        self.sparql_exec = SparqlExecutor(endpoint_url)

        # Pre-extract keywords from the knowledge graph
        self.extracted_keywords = self.extract_keywords_from_kg()

        # Fallback keywords in case extraction fails
        self.fallback_keywords = [
            "PEMERINTAH",
            "REPUBLIK",
            "INDONESIA",
            "UNDANG",
            "PERATURAN",
            "HUKUM",
            "NEGARA",
            "KESEHATAN",
            "PENDIDIKAN",
            "LINGKUNGAN",
            "KETENAGAKERJAAN",
            "PAJAK",
            "INVESTASI",
            "PENGESAHAN",
            "PENETAPAN",
        ]

        print(
            f"Extracted {len(self.extracted_keywords)} keywords from the knowledge graph"
        )

    def extract_keywords_from_kg(self):
        """
        Extract meaningful keywords from law titles in the knowledge graph

        Returns:
            list: List of keywords that appear in law titles
        """
        try:
            # Query to get all law titles
            query = """
            SELECT ?title
            WHERE {
                ?law <https://example.org/lex2kg/ontology/tentang> ?title .
            }
            """

            results = self.sparql_exec.execute_query(query)
            if not results:
                print("No titles found in the knowledge graph")
                return []

            # Process titles and extract meaningful words
            all_words = []
            for result in results:
                if "title" in result:
                    title = str(result["title"])
                    # Split by spaces and filter for meaningful words (5+ characters)
                    title_words = [w.upper() for w in title.split() if len(w) >= 5]
                    all_words.extend(title_words)

            # Count frequency of each word
            word_counts = Counter(all_words)

            # Select words that appear at least twice (more meaningful)
            common_words = [word for word, count in word_counts.items() if count >= 2]

            # If we don't have enough common words, include all words
            if len(common_words) < 10:
                common_words = list(set(all_words))

            print(f"Found {len(common_words)} common words in law titles")
            return common_words

        except Exception as e:
            print(f"Error extracting keywords from knowledge graph: {e}")
            return []

    def initialize_templates(self):
        """
        Initialize question-query template pairs for legal document data with multiple question variations

        Returns:
            list: Templates for different question types and complexity levels
        """
        # Legal document specific templates - ORGANIZED BY COMPLEXITY
        legal_templates = [
            # ==================== BASIC TEMPLATES ====================
            # Direct property retrieval (single triple pattern)
            {
                "id": "law-title",
                "category": "legal",
                "questionTemplates": [
                    "Apa judul dari {entity}?",
                    "Apa nama dari {entity}?",
                    "Bagaimana judul dari {entity}?",
                ],
                "englishQuestions": [
                    "What is the title of {entity}?",
                    "What is the name of {entity}?",
                    "How is the title of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    {entity} lex2kg-o:tentang ?title .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-enactment-date",
                "category": "legal",
                "questionTemplates": [
                    "Kapan {entity} disahkan?",
                    "Pada tanggal berapa {entity} disahkan?",
                    "Tanggal berapakah {entity} disahkan?",
                ],
                "englishQuestions": [
                    "When was {entity} enacted?",
                    "On what date was {entity} enacted?",
                    "What date was {entity} enacted on?",
                ],
                "sparqlTemplate": """
                    SELECT ?date WHERE {
                    {entity} lex2kg-o:disahkanPada ?date .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-enactment-location",
                "category": "legal",
                "questionTemplates": [
                    "Di mana {entity} disahkan?",
                    "Di kota manakah {entity} disahkan?",
                    "Di lokasi mana {entity} disahkan?",
                ],
                "englishQuestions": [
                    "Where was {entity} enacted?",
                    "In which city was {entity} enacted?",
                    "At what location was {entity} enacted?",
                ],
                "sparqlTemplate": """
                    SELECT ?location WHERE {
                    {entity} lex2kg-o:disahkanDi ?location .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-enactment-person",
                "category": "legal",
                "questionTemplates": [
                    "Siapa yang mengesahkan {entity}?",
                    "Oleh siapa {entity} disahkan?",
                    "Siapa pengesah {entity}?",
                ],
                "englishQuestions": [
                    "Who enacted {entity}?",
                    "By whom was {entity} enacted?",
                    "Who was the enactor of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?person WHERE {
                    {entity} lex2kg-o:disahkanOleh ?person .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-enactment-position",
                "category": "legal",
                "questionTemplates": [
                    "Apa jabatan pengesah {entity}?",
                    "Apa posisi orang yang mengesahkan {entity}?",
                    "Jabatan apa yang dimiliki pengesah {entity}?",
                ],
                "englishQuestions": [
                    "What is the position of the person who enacted {entity}?",
                    "What role did the enactor of {entity} hold?",
                    "What was the official title of the person who enacted {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?position WHERE {
                    {entity} lex2kg-o:jabatanPengesah ?position .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-type",
                "category": "legal",
                "questionTemplates": [
                    "Apa jenis peraturan dari {entity}?",
                    "Termasuk jenis peraturan apa {entity}?",
                    "Kategori peraturan apa {entity}?",
                ],
                "englishQuestions": [
                    "What type of regulation is {entity}?",
                    "Which type of regulation does {entity} belong to?",
                    "What category of regulation is {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?type WHERE {
                    {entity} lex2kg-o:jenisPeraturan ?type .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-year",
                "category": "legal",
                "questionTemplates": [
                    "Pada tahun berapa {entity} disahkan?",
                    "Tahun berapakah {entity} disahkan?",
                    "Kapan tahun pengesahan {entity}?",
                ],
                "englishQuestions": [
                    "In what year was {entity} enacted?",
                    "Which year was {entity} enacted in?",
                    "When was the year of {entity}'s enactment?",
                ],
                "sparqlTemplate": """
                    SELECT ?year WHERE {
                    {entity} lex2kg-o:tahun ?year .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-number",
                "category": "legal",
                "questionTemplates": [
                    "Berapa nomor dari {entity}?",
                    "Nomor berapakah {entity}?",
                    "Apa nomor {entity}?",
                ],
                "englishQuestions": [
                    "What is the number of {entity}?",
                    "Which number is {entity}?",
                    "What number was assigned to {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?number WHERE {
                    {entity} lex2kg-o:nomor ?number .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-jurisdiction",
                "category": "legal",
                "questionTemplates": [
                    "Apa yurisdiksi dari {entity}?",
                    "Di bawah yurisdiksi apa {entity} berlaku?",
                    "Wilayah hukum apa yang mencakup {entity}?",
                ],
                "englishQuestions": [
                    "What is the jurisdiction of {entity}?",
                    "Under which jurisdiction does {entity} apply?",
                    "What legal territory covers {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?jurisdiction WHERE {
                    {entity} lex2kg-o:yurisdiksi ?jurisdiction .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-language",
                "category": "legal",
                "questionTemplates": [
                    "Dalam bahasa apa {entity} ditulis?",
                    "Bahasa apa yang digunakan dalam {entity}?",
                    "Apa bahasa penulisan {entity}?",
                ],
                "englishQuestions": [
                    "In what language is {entity} written?",
                    "What language was used in {entity}?",
                    "What is the language of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?language WHERE {
                    {entity} lex2kg-o:bahasa ?language .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-menimbang",
                "category": "legal",
                "questionTemplates": [
                    "Apa yang menjadi pertimbangan dari {entity}?",
                    "Apa pertimbangan dalam {entity}?",
                    "Apa dasar pertimbangan {entity}?",
                ],
                "englishQuestions": [
                    "What are the considerations of {entity}?",
                    "What considerations are included in {entity}?",
                    "What is the basis of consideration for {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?menimbang WHERE {
                    {entity} lex2kg-o:menimbang ?menimbang .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-mengingat",
                "category": "legal",
                "questionTemplates": [
                    "Apa yang menjadi dasar hukum dari {entity}?",
                    "Apa dasar hukum {entity}?",
                    "Apa rujukan hukum untuk {entity}?",
                ],
                "englishQuestions": [
                    "What is the legal basis of {entity}?",
                    "What legal basis does {entity} have?",
                    "What are the legal references for {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?mengingat WHERE {
                    {entity} lex2kg-o:mengingat ?mengingat .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "article-text",
                "category": "legal",
                "questionTemplates": [
                    "Apa isi dari {entity}?",
                    "Bagaimana bunyi {entity}?",
                    "Apa konten dari {entity}?",
                ],
                "englishQuestions": [
                    "What is the content of {entity}?",
                    "How does {entity} read?",
                    "What is the text of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?text WHERE {
                    {entity} lex2kg-o:teks ?text .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "article-version",
                "category": "legal",
                "questionTemplates": [
                    "Apa versi terbaru dari {entity}?",
                    "Versi berapa {entity} saat ini?",
                    "Apa versi terakhir dari {entity}?",
                ],
                "englishQuestions": [
                    "What is the latest version of {entity}?",
                    "Which version of {entity} is current?",
                    "What is the most recent version of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?version WHERE {
                    {entity} lex2kg-o:versi ?version .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "chapter-title",
                "category": "legal",
                "questionTemplates": [
                    "Apa judul dari {entity}?",
                    "Apa nama {entity}?",
                    "Apa judul bab {entity}?",
                ],
                "englishQuestions": [
                    "What is the title of {entity}?",
                    "What is the name of {entity}?",
                    "What is the chapter title of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    {entity} lex2kg-o:judul ?title .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "article-letters",
                "category": "legal",
                "questionTemplates": [
                    "Apa saja huruf yang terdapat dalam {entity}?",
                    "Huruf apa saja yang ada di {entity}?",
                    "Apa huruf-huruf dalam {entity}?",
                ],
                "englishQuestions": [
                    "What letters are in {entity}?",
                    "Which letters can be found in {entity}?",
                    "What are the letters included in {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?letter WHERE {
                    {entity} lex2kg-o:huruf ?letter .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "law-references-what",
                "category": "legal",
                "questionTemplates": [
                    "Apa saja yang dirujuk oleh {entity}?",
                    "Dokumen apa yang direferensikan oleh {entity}?",
                    "Apa rujukan dari {entity}?",
                ],
                "englishQuestions": [
                    "What does {entity} reference?",
                    "Which documents are referenced by {entity}?",
                    "What are the references from {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?referenced WHERE {
                    {entity} lex2kg-o:merujuk ?referenced .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "what-amended-law",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang mengubah {entity}?",
                    "Peraturan apa yang telah mengamendemen {entity}?",
                    "Apa saja peraturan yang memodifikasi {entity}?",
                ],
                "englishQuestions": [
                    "Which laws amended {entity}?",
                    "What regulations have amended {entity}?",
                    "Which regulations have modified {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?amendingLaw WHERE {
                    ?amendingLaw lex2kg-o:mengubah {entity} .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "laws-deleted-what",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang dihapus oleh {entity}?",
                    "Peraturan apa yang telah dicabut oleh {entity}?",
                    "Apa saja peraturan yang dibatalkan oleh {entity}?",
                ],
                "englishQuestions": [
                    "Which laws were deleted by {entity}?",
                    "What regulations have been revoked by {entity}?",
                    "Which regulations were canceled by {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?deletedLaw WHERE {
                    {entity} lex2kg-o:menghapus ?deletedLaw .
                    }
                """,
                "complexity": "basic",
            },
            {
                "id": "what-deleted-law",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang menghapus {entity}?",
                    "Peraturan apa yang telah mencabut {entity}?",
                    "Apa saja peraturan yang membatalkan {entity}?",
                ],
                "englishQuestions": [
                    "Which laws deleted {entity}?",
                    "What regulations have revoked {entity}?",
                    "Which regulations have canceled {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?deletingLaw WHERE {
                    ?deletingLaw lex2kg-o:menghapus {entity} .
                    }
                """,
                "complexity": "basic",
            },
            # ==================== INTERMEDIATE TEMPLATES ====================
            # Counting, filtering, simple joins, or multiple patterns
            {
                "id": "law-articles",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah pasal dalam {entity}?",
                    "Ada berapa pasal di dalam {entity}?",
                    "Berapa banyak pasal yang terdapat dalam {entity}?",
                ],
                "englishQuestions": [
                    "How many articles are in {entity}?",
                    "What is the number of articles in {entity}?",
                    "How many articles does {entity} contain?",
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?article) AS ?count) WHERE {
                    {entity} lex2kg-o:pasal ?article .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "law-chapters",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah bab dalam {entity}?",
                    "Ada berapa bab di dalam {entity}?",
                    "Berapa banyak bab yang terdapat dalam {entity}?",
                ],
                "englishQuestions": [
                    "How many chapters are in {entity}?",
                    "What is the number of chapters in {entity}?",
                    "How many chapters does {entity} contain?",
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?chapter) AS ?count) WHERE {
                    {entity} lex2kg-o:bab ?chapter .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "article-sections",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah ayat dalam {entity}?",
                    "Ada berapa ayat di dalam {entity}?",
                    "Berapa banyak ayat yang terdapat dalam {entity}?",
                ],
                "englishQuestions": [
                    "How many sections are in {entity}?",
                    "What is the number of sections in {entity}?",
                    "How many sections does {entity} contain?",
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?section) AS ?count) WHERE {
                    {entity} lex2kg-o:versi ?version .
                    ?version lex2kg-o:ayat ?section .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "count-article-letters",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah huruf dalam {entity}?",
                    "Ada berapa huruf di dalam {entity}?",
                    "Berapa banyak huruf yang terdapat dalam {entity}?",
                ],
                "englishQuestions": [
                    "How many letters are in {entity}?",
                    "What is the number of letters in {entity}?",
                    "How many letters does {entity} contain?",
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?letter) AS ?count) WHERE {
                    {entity} lex2kg-o:huruf ?letter .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "laws-enacted-in-year",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang disahkan pada tahun {value}?",
                    "Peraturan apa saja yang dibuat pada tahun {value}?",
                    "Apa saja perundangan yang ditetapkan di tahun {value}?",
                ],
                "englishQuestions": [
                    "What laws were enacted in the year {value}?",
                    "Which regulations were created in {value}?",
                    "What legislation was established in the year {value}?",
                ],
                "sparqlTemplate": """
                    SELECT ?law ?title WHERE {
                    ?law lex2kg-o:tahun {value} .
                    ?law lex2kg-o:tentang ?title .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "law-parts",
                "category": "legal",
                "questionTemplates": [
                    "Apa saja bagian dari {entity}?",
                    "Bagian apa saja yang terdapat dalam {entity}?",
                    "Sebutkan bagian-bagian dari {entity}?",
                ],
                "englishQuestions": [
                    "What are the parts of {entity}?",
                    "Which components are contained in {entity}?",
                    "List the sections of {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?part ?type WHERE {
                    { {entity} lex2kg-o:pasal ?part . BIND("pasal" AS ?type) }
                    UNION
                    { {entity} lex2kg-o:bab ?part . BIND("bab" AS ?type) }
                    UNION
                    { {entity} lex2kg-o:bagian ?part . BIND("bagian" AS ?type) }
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "article-subsections",
                "category": "legal",
                "questionTemplates": [
                    "Apa saja ayat yang terdapat dalam {entity}?",
                    "Ayat apa saja yang ada di {entity}?",
                    "Sebutkan ayat-ayat dalam {entity}?",
                ],
                "englishQuestions": [
                    "What sections are in {entity}?",
                    "Which subsections exist in {entity}?",
                    "List the paragraphs in {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT ?section WHERE {
                    {entity} lex2kg-o:versi ?version .
                    ?version lex2kg-o:ayat ?section .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "article-references",
                "category": "legal",
                "questionTemplates": [
                    "Pasal mana saja yang merujuk ke {entity}?",
                    "Pasal apa yang mengacu pada {entity}?",
                    "Pasal-pasal apa yang mereferensikan {entity}?",
                ],
                "englishQuestions": [
                    "Which articles reference {entity}?",
                    "What articles refer to {entity}?",
                    "Which articles cite {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?referringArticle ?text WHERE {
                    ?referringArticle lex2kg-o:merujuk {entity} .
                    ?referringArticle lex2kg-o:teks ?text .
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "law-by-keyword",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang berhubungan dengan '{value}'?",
                    "Peraturan apa yang terkait dengan '{value}'?",
                    "Apa saja regulasi mengenai '{value}'?",
                ],
                "englishQuestions": [
                    "Which laws are related to '{value}'?",
                    "What regulations are associated with '{value}'?",
                    "What are the regulations concerning '{value}'?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?law ?title WHERE {
                    ?law lex2kg-o:tentang ?title .
                    FILTER(CONTAINS(LCASE(?title), LCASE({value})))
                    }
                """,
                "complexity": "intermediate",
            },
            {
                "id": "law-by-enactor",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang disahkan oleh {value}?",
                    "Peraturan apa yang ditandatangani oleh {value}?",
                    "Apa saja regulasi yang disahkan {value}?",
                ],
                "englishQuestions": [
                    "What laws were enacted by {value}?",
                    "Which regulations were signed by {value}?",
                    "What regulations did {value} enact?",
                ],
                "sparqlTemplate": """
                    SELECT ?law ?title ?date WHERE {
                    ?law lex2kg-o:disahkanOleh {value} .
                    ?law lex2kg-o:tentang ?title .
                    ?law lex2kg-o:disahkanPada ?date .
                    }
                    ORDER BY DESC(?date)
                """,
                "complexity": "intermediate",
            },
            # ==================== ADVANCED TEMPLATES ====================
            # Complex joins, aggregations, or multi-step queries
            {
                "id": "laws-amended-what",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang diubah oleh {entity}?",
                    "Peraturan apa yang diamendemen oleh {entity}?",
                    "Apa saja regulasi yang dimodifikasi oleh {entity}?",
                ],
                "englishQuestions": [
                    "Which laws were amended by {entity}?",
                    "What regulations were modified by {entity}?",
                    "Which legislation was changed by {entity}?",
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?amendedLaw ?title WHERE {
                    {entity} lex2kg-o:mengubah ?versi .
                    ?pasal lex2kg-o:versi ?versi .
                    ?amendedLaw lex2kg-o:pasal ?pasal .
                    ?amendedLaw lex2kg-o:tentang ?title .
                    }
                """,
                "complexity": "advanced",
            },
            {
                "id": "law-with-most-articles",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang mana yang memiliki pasal terbanyak?",
                    "Peraturan apa yang mempunyai jumlah pasal paling banyak?",
                    "UU mana dengan jumlah pasal terbesar?",
                ],
                "englishQuestions": [
                    "Which law has the most articles?",
                    "What regulation has the highest number of articles?",
                    "Which legislation contains the greatest number of articles?",
                ],
                "sparqlTemplate": """
                    SELECT ?law ?title (COUNT(?article) AS ?articleCount) WHERE {
                    ?law lex2kg-o:tentang ?title .
                    ?law lex2kg-o:pasal ?article .
                    }
                    GROUP BY ?law ?title
                    ORDER BY DESC(?articleCount)
                    LIMIT 1
                """,
                "complexity": "advanced",
            },
        ]

        # Only use legal templates, ignoring any custom templates
        # to focus specifically on legal document data
        return legal_templates

    def generate_dataset(
        self,
        size=1000,
        complexity_distribution=None,
        include_variations=True,
        variations_per_question=3,
        validate_queries=False,
        max_attempts_per_template=15,
    ):
        """
        Generate dataset based on legal document knowledge graph

        Args:
            size (int): Total number of question-query pairs to generate
            complexity_distribution (dict): Distribution of complexity levels
            include_variations (bool): Whether to include variations of questions
            variations_per_question (int): Number of variations per question
            validate_queries (bool): Whether to validate SPARQL queries
            max_attempts_per_template (int): Maximum number of attempts to instantiate a template

        Returns:
            list: Array of question-SPARQL pairs
        """
        if complexity_distribution is None:
            complexity_distribution = {
                "basic": 0.5,
                "intermediate": 0.3,
                "advanced": 0.2,
            }

        dataset = []
        id_counter = 1

        # Calculate how many questions of each complexity to generate
        counts_by_complexity = {}
        for complexity, proportion in complexity_distribution.items():
            counts_by_complexity[complexity] = int(size * proportion)

        # Track problematic templates for reporting
        failed_templates = {}
        success_templates = {}

        # Generate questions for each complexity level
        for complexity, count in counts_by_complexity.items():
            successful_generations = 0
            eligible_templates = [
                t for t in self.templates if t["complexity"] == complexity
            ]

            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue

            # Try to generate the required number for this complexity
            while successful_generations < count and len(dataset) < size:
                # Randomly select a template for this complexity level
                template = random.choice(eligible_templates)

                # Track attempts for this template
                template_id = template["id"]
                if template_id not in success_templates:
                    success_templates[template_id] = 0
                if template_id not in failed_templates:
                    failed_templates[template_id] = 0

                # Try to instantiate this template up to max_attempts
                attempts = 0
                success = False

                while attempts < max_attempts_per_template and not success:
                    attempts += 1
                    try:
                        # Use the discovery-based approach to instantiate the template
                        instance = self.instantiate_template_with_discovery(template)

                        if instance:
                            # Success! Add the question-query pair
                            dataset.append(
                                {
                                    "id": f"q{id_counter}",
                                    "question": instance["question"],
                                    "englishQuestion": instance["englishQuestion"],
                                    "sparql": instance["sparql"],
                                    "category": template["category"],
                                    "complexity": template["complexity"],
                                    "templateId": template["id"],
                                }
                            )
                            id_counter += 1
                            successful_generations += 1
                            success_templates[template_id] += 1
                            success = True

                            # Add variations if requested
                            if include_variations and instance["question"]:
                                variations = (
                                    self.variation_generator.generate_variations(
                                        instance["question"],
                                        instance["englishQuestion"],
                                        template["category"],
                                        min(variations_per_question, 5),
                                    )
                                )

                                for variation in variations:
                                    if len(dataset) >= size:
                                        break

                                    dataset.append(
                                        {
                                            "id": f"q{id_counter}",
                                            "question": variation["indonesian"],
                                            "englishQuestion": variation["english"],
                                            "sparql": instance["sparql"],
                                            "category": template["category"],
                                            "complexity": template["complexity"],
                                            "templateId": template["id"],
                                            "isVariation": True,
                                        }
                                    )
                                    id_counter += 1
                    except Exception as e:
                        print(
                            f"Error instantiating template {template['id']} (attempt {attempts}): {e}"
                        )

                # If we've tried max_attempts and still failed, record this template as problematic
                if not success:
                    failed_templates[template_id] += 1

        # Report template success and failure rates
        print("\nTemplate success/failure statistics:")
        for template_id in set(success_templates.keys()) | set(failed_templates.keys()):
            success_count = success_templates.get(template_id, 0)
            failure_count = failed_templates.get(template_id, 0)
            total = success_count + failure_count
            success_rate = (success_count / total * 100) if total > 0 else 0
            print(
                f"  - {template_id}: {success_count} successes, {failure_count} failures ({success_rate:.1f}% success rate)"
            )

        # Report complexity distribution achieved
        complexity_counts = {}
        for item in dataset:
            complexity = item["complexity"]
            if complexity not in complexity_counts:
                complexity_counts[complexity] = 0
            complexity_counts[complexity] += 1

        print("\nActual complexity distribution in generated dataset:")
        for complexity, count in complexity_counts.items():
            target = counts_by_complexity.get(complexity, 0)
            percentage = (count / len(dataset)) * 100 if dataset else 0
            print(
                f"  - {complexity}: {count}/{len(dataset)} ({percentage:.1f}%) [Target: {target}]"
            )

        # Validate queries if requested
        if validate_queries:
            filtered_dataset = []

            for item in dataset:
                try:
                    # Execute the query to validate it
                    results = self.sparql_exec.execute_query(
                        item["sparql"], return_format="dict"
                    )
                    filtered_dataset.append(item)
                except Exception as e:
                    print(f"Invalid SPARQL query for id {item['id']}: {e}")

            return filtered_dataset

        return dataset

    def instantiate_template_with_discovery(self, template):
        """
        Instantiate a template using a discovery-based approach that guarantees valid placeholder values

        Args:
            template (dict): The template to instantiate

        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Extract placeholders from the template
        placeholders = self.extract_placeholders(template)

        # Special handling for law-by-keyword template
        if "law-by-keyword" in template["id"] and "value" in placeholders:
            # For this template, use the pre-extracted keywords directly
            # rather than trying to discover them via SPARQL
            return self.instantiate_keyword_template(template)

        # Create a discovery query that includes all placeholders in the SELECT clause
        discovery_query = self.create_discovery_query(template, placeholders)

        if not discovery_query:
            print(f"Could not create discovery query for template: {template['id']}")
            return self.instantiate_template(template)

        # Execute the discovery query
        try:
            print(f"Executing discovery query for template {template['id']}...")
            results = self.sparql_exec.execute_query(discovery_query)

            if not results:
                print(f"No valid combinations found for template: {template['id']}")
                print("Query: ", discovery_query)
                return self.instantiate_template(template)

            print(
                f"Found {len(results)} valid combinations for template: {template['id']}"
            )

            # Randomly select one complete valid combination of values
            selected = random.choice(results)

            # Create a mapping of placeholders to their values from the selected combination
            replacements = {}

            # Extract values for each placeholder
            for placeholder in placeholders:
                # Skip if placeholder doesn't exist in result
                if placeholder not in selected:
                    print(
                        f"Warning: Placeholder {placeholder} not found in query results"
                    )
                    continue

                value = selected[placeholder]

                # Skip if value is None
                if value is None:
                    print(f"Warning: Placeholder {placeholder} has None value")
                    continue

                # Try to get the label for entity placeholders
                if placeholder.startswith("entity"):
                    entity_uri = str(value)

                    # Look for a label variable for this entity
                    label_var = f"{placeholder}Label"
                    if label_var in selected and selected[label_var] is not None:
                        entity_label = str(selected[label_var])
                    else:
                        # Extract label from URI if not found in result
                        entity_label = self.extract_label_from_uri(entity_uri)

                    replacement = {
                        "value": self.shorten_uri(entity_uri),
                        "label": entity_label,
                        "uri": entity_uri,
                    }
                elif placeholder == "value" or placeholder.endswith("Value"):
                    # For value placeholders
                    value_str = str(value)

                    # Handle different value types appropriately
                    if (
                        "year" in template["id"]
                        or "year" in template["questionTemplate"].lower()
                    ):
                        replacement = {"value": value_str, "label": value_str}
                    elif (
                        "keyword" in template["id"]
                        or "keyword" in template["questionTemplate"].lower()
                    ):
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"',  # Include quotes for string literal
                        }
                    elif (
                        "enactor" in template["id"]
                        or "enactor" in template["questionTemplate"].lower()
                    ):
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"',  # Include quotes for string literal
                        }
                    else:
                        replacement = {"value": value_str, "label": value_str}
                else:
                    # For other placeholders, use as is
                    replacement = {"value": str(value), "label": str(value)}

                replacements[placeholder] = replacement

            # Check if all placeholders have valid replacements
            if set(replacements.keys()) != set(placeholders):
                missing = set(placeholders) - set(replacements.keys())
                print(f"Missing valid values for placeholders: {missing}")
                return self.instantiate_template(template)

            # Randomly select one of the question templates
            if "questionTemplates" in template and template["questionTemplates"]:
                idx = random.randrange(len(template["questionTemplates"]))
                question_template = template["questionTemplates"][idx]
                english_question_template = (
                    template["englishQuestions"][idx]
                    if idx < len(template["englishQuestions"])
                    else template["englishQuestions"][0]
                )
            else:
                # Fallback to single template for backward compatibility
                question_template = template.get("questionTemplate", "")
                english_question_template = template.get("englishQuestion", "")

            # Apply replacements to the question template
            question = question_template.strip()
            english_question = english_question_template.strip()
            sparql = template["sparqlTemplate"].strip()

            # Replace placeholders in question and query
            for placeholder, replacement in replacements.items():
                # Create a pattern that can handle whitespace around the placeholder
                pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"

                # Replace in question
                replacement_text = replacement.get(
                    "label", replacement.get("value", "")
                )
                question = re.sub(pattern, replacement_text, question)
                english_question = re.sub(pattern, replacement_text, english_question)

                # Replace in SPARQL
                if "uri" in replacement:
                    sparql_value = f"<{replacement['uri']}>"
                elif "sparqlValue" in replacement:
                    sparql_value = replacement["sparqlValue"]
                else:
                    sparql_value = replacement["value"]

                sparql = re.sub(pattern, sparql_value, sparql)

            # Replace all prefixed URIs with full URIs
            for prefix, uri in self.prefixes.items():
                pattern = r"\b" + re.escape(prefix) + r":([a-zA-Z0-9_]+)\b"
                sparql = re.sub(pattern, r"<" + uri + r"\1>", sparql)

            # Format the SPARQL query for readability
            sparql = self.format_sparql(sparql)

            return {
                "question": question,
                "englishQuestion": english_question,
                "sparql": sparql,
            }

        except Exception as e:
            print(f"Error executing discovery query for template {template['id']}: {e}")
            # Fall back to the old method
            return self.instantiate_template(template)

    def instantiate_keyword_template(self, template):
        """
        Special handler for law-by-keyword template using pre-extracted keywords
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Get a keyword from our pre-extracted list
        keyword = self.select_keyword_value()
        
        # Apply the keyword to the template
        replacements = {"value": keyword}
        
        # Randomly select one of the question templates
        if "questionTemplates" in template and template["questionTemplates"]:
            idx = random.randrange(len(template["questionTemplates"]))
            question_template = template["questionTemplates"][idx]
            english_question_template = template["englishQuestions"][idx] if idx < len(template["englishQuestions"]) else template["englishQuestions"][0]
        else:
            # Fallback to single template for backward compatibility
            question_template = template.get("questionTemplate", "")
            english_question_template = template.get("englishQuestion", "")
        
        # Apply replacements to the question template
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Replace the placeholder in question and query
        pattern = r"{[\s]*value[\s]*}"
        
        # Replace in question
        replacement_text = keyword.get("label", keyword.get("value", ""))
        question = re.sub(pattern, replacement_text, question)
        english_question = re.sub(pattern, replacement_text, english_question)
        
        # Replace in SPARQL
        sparql_value = keyword.get("sparqlValue", f'"{keyword["value"]}"')
        
        sparql = re.sub(pattern, sparql_value, sparql)
        
        # Replace all prefixed URIs with full URIs
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}

    def create_discovery_query(self, template, placeholders):
        """
        Create a discovery query that finds valid values for all placeholders

        Args:
            template (dict): The template to convert
            placeholders (set): Set of placeholders in the template

        Returns:
            str: The discovery query
        """
        sparql_template = template["sparqlTemplate"].strip()

        # Special handling for law-by-keyword template
        if "law-by-keyword" in template["id"] and "value" in placeholders:
            # For this template, we'll use our pre-extracted keywords
            # rather than trying to discover them from the SPARQL endpoint
            return None

        # Extract the WHERE clause from the template
        where_match = re.search(
            r"WHERE\s*{(.*)}", sparql_template, re.DOTALL | re.IGNORECASE
        )
        if not where_match:
            print(
                f"Error: Could not extract WHERE clause from template: {template['id']}"
            )
            return None

        where_clause = where_match.group(1).strip()

        # Replace placeholders with variables in the WHERE clause, handling quoted placeholders
        for placeholder in placeholders:
            # First, handle quoted placeholders - replace "{placeholder}" with the variable without quotes
            quoted_pattern = r'"{\s*' + re.escape(placeholder) + r'\s*}"'
            where_clause = re.sub(quoted_pattern, f"?{placeholder}", where_clause)

            # Then handle regular placeholders
            regular_pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
            where_clause = re.sub(regular_pattern, f"?{placeholder}", where_clause)

        # Build SELECT clause with all placeholders
        select_vars = []

        # Add the result variable from the original query
        result_var_match = re.search(
            r"SELECT\s+(?:\(.*\)\s+AS\s+)?(\?\w+)", sparql_template, re.IGNORECASE
        )
        if result_var_match:
            result_var = result_var_match.group(1)
            if "COUNT" not in result_var and "count" not in result_var:
                select_vars.append(result_var)

        # Add all placeholder variables to SELECT clause
        for placeholder in placeholders:
            select_vars.append(f"?{placeholder}")
            # For entity placeholders, also select label if available
            if placeholder.startswith("entity"):
                select_vars.append(f"?{placeholder}Label")

        # Construct the SELECT clause with all variables
        select_clause = "SELECT DISTINCT " + " ".join(select_vars)

        # Construct the complete discovery query
        discovery_query = f"{select_clause} WHERE {{ {where_clause}"

        # Add OPTIONAL label patterns for entity placeholders
        for placeholder in placeholders:
            if placeholder.startswith("entity"):
                discovery_query += (
                    f" OPTIONAL {{ ?{placeholder} rdfs:label ?{placeholder}Label . }}"
                )

        # Close the query with increased LIMIT to ensure finding valid combinations
        discovery_query += " }"

        # Replace all prefixed URIs with full URIs for consistency
        for prefix, uri in self.prefixes.items():
            pattern = r"\b" + re.escape(prefix) + r":([a-zA-Z0-9_]+)\b"
            discovery_query = re.sub(pattern, r"<" + uri + r"\1>", discovery_query)

        return discovery_query

    def instantiate_template(self, template):
        """
        Original method to instantiate a template with specific entities and properties
        Kept as a fallback method

        Args:
            template (dict): The template to instantiate

        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Select entities and properties appropriate for this template
        placeholders = self.extract_placeholders(template)
        replacements = self.select_replacements(placeholders, template)

        if not replacements:
            return None

        # Randomly select one of the question templates
        if "questionTemplates" in template and template["questionTemplates"]:
            idx = random.randrange(len(template["questionTemplates"]))
            question_template = template["questionTemplates"][idx]
            english_question_template = (
                template["englishQuestions"][idx]
                if idx < len(template["englishQuestions"])
                else template["englishQuestions"][0]
            )
        else:
            # Fallback to single template for backward compatibility
            question_template = template.get("questionTemplate", "")
            english_question_template = template.get("englishQuestion", "")

        # Apply replacements to the question template
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()

        # Add prefixes to SPARQL query
        prefix_string = ""
        for prefix, uri in self.prefixes.items():
            pattern = r"\b" + re.escape(prefix) + r":([a-zA-Z0-9_]+)\b"
            sparql = re.sub(pattern, r"<" + uri + r"\1>", sparql)

        sparql = prefix_string + sparql

        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            # Create a pattern that can handle whitespace around the placeholder
            pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"

            # Replace in question
            replacement_text = replacement.get("label", replacement.get("value", ""))
            question = re.sub(pattern, replacement_text, question)
            english_question = re.sub(pattern, replacement_text, english_question)

            # Replace in SPARQL
            if "uri" in replacement:
                sparql_value = f"<{replacement['uri']}>"
            elif "sparqlValue" in replacement:
                sparql_value = replacement["sparqlValue"]
            else:
                sparql_value = replacement["value"]

            sparql = re.sub(pattern, sparql_value, sparql)

        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)

        return {
            "question": question,
            "englishQuestion": english_question,
            "sparql": sparql,
        }
        """
        Original method to instantiate a template with specific entities and properties
        Kept as a fallback method
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Select entities and properties appropriate for this template
        placeholders = self.extract_placeholders(template)
        replacements = self.select_replacements(placeholders, template)

        if not replacements:
            return None

        # Apply replacements to the question template
        question = template["questionTemplate"].strip()
        english_question = template["englishQuestion"].strip()
        sparql = template["sparqlTemplate"].strip()

        # Add prefixes to SPARQL query
        prefix_string = ""
        for prefix, uri in self.prefixes.items():
            pattern = r"\b" + re.escape(prefix) + r":([a-zA-Z0-9_]+)\b"
            sparql = re.sub(pattern, r"<" + uri + r"\1>", sparql)

        sparql = prefix_string + sparql

        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            # Create a pattern that can handle whitespace around the placeholder
            pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"

            # Replace in question
            replacement_text = replacement.get("label", replacement.get("value", ""))
            question = re.sub(pattern, replacement_text, question)
            english_question = re.sub(pattern, replacement_text, english_question)

            # Replace in SPARQL
            if "uri" in replacement:
                sparql_value = f"<{replacement['uri']}>"
            elif "sparqlValue" in replacement:
                sparql_value = replacement["sparqlValue"]
            else:
                sparql_value = replacement["value"]

            sparql = re.sub(pattern, sparql_value, sparql)

        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)

        return {
            "question": question,
            "englishQuestion": english_question,
            "sparql": sparql,
        }

    def extract_placeholders(self, template):
        """
        Extract all placeholders from template

        Args:
            template (dict): Template with question and SPARQL

        Returns:
            set: Set of placeholder names
        """
        placeholders = set()

        # Check if we have multiple question templates or a single one
        if "questionTemplates" in template and template["questionTemplates"]:
            question_templates = template["questionTemplates"]
            english_templates = template.get("englishQuestions", [])
        else:
            # Fallback to single template
            question_templates = [template.get("questionTemplate", "")]
            english_templates = [template.get("englishQuestion", "")]

        # For Python triple-quoted strings, we need to handle whitespace
        # First, normalize the SPARQL template
        sparql_template = template["sparqlTemplate"].strip()

        # Use a pattern that can handle potential whitespace around the placeholders
        pattern = r"{([^{}\n\r]+)}"

        # Search in all question templates
        for qt in question_templates:
            qt = qt.strip()
            for match in re.finditer(pattern, qt):
                placeholders.add(match.group(1).strip())

        # Search in all English question templates
        for et in english_templates:
            et = et.strip()
            for match in re.finditer(pattern, et):
                placeholders.add(match.group(1).strip())

        # Search in SPARQL template
        for match in re.finditer(pattern, sparql_template):
            placeholders.add(match.group(1).strip())

        return placeholders

    def select_replacements(self, placeholders, template):
        """
        Select appropriate replacements for template placeholders

        Args:
            placeholders (set): Set of placeholder names
            template (dict): The template being instantiated

        Returns:
            dict: Map of placeholder to replacement value or None if failed
        """
        replacements = {}

        # Try to select appropriate values for each placeholder
        for placeholder in placeholders:
            replacement = None

            # Handle entity placeholders
            if placeholder.startswith("entity"):
                replacement = self.select_entity_from_endpoint(template)

                # If we didn't get a replacement, try pattern-based selection
                if not replacement:
                    # Select entity based on template type
                    if "law-" in template["id"]:
                        # For law templates, select a UU entity
                        replacement = self.select_entity_by_pattern("uu/")
                    elif "article" in template["id"]:
                        # For article templates, select a pasal entity
                        replacement = self.select_entity_by_pattern("pasal/")
                    elif "chapter" in template["id"]:
                        # For chapter templates, select a bab entity
                        replacement = self.select_entity_by_pattern("bab/")
                    else:
                        # Default to any entity
                        replacement = self.select_random_entity()

                # Fallback to any entity if specific type not found
                if not replacement:
                    replacement = self.select_random_entity()

            # Handle value placeholders
            elif placeholder == "value" or placeholder.endswith("Value"):
                replacement = self.select_value_from_endpoint(template, placeholder)

                # If we didn't get a replacement, use predefined values
                if not replacement:
                    if "law-by-enactor" in template["id"]:
                        # For law by enactor, use a person name
                        replacement = self.select_enactor_value()
                    elif "laws-enacted-in-year" in template["id"]:
                        # For laws by year, use a year
                        replacement = self.select_year_value()
                    elif "law-by-keyword" in template["id"]:
                        # For laws by keyword, use a keyword
                        replacement = self.select_keyword_value()
                    else:
                        replacement = self.select_random_value(template)

            # Handle property placeholders
            elif placeholder.startswith("property"):
                replacement = self.select_legal_property(template, placeholder)

            # If we couldn't find a replacement, return None
            if not replacement:
                print(f"Could not find replacement for placeholder: {placeholder}")
                return None

            replacements[placeholder] = replacement

        return replacements

    def select_entity_from_endpoint(self, template):
        """
        Select an entity from the SPARQL endpoint that fits the template

        Args:
            template (dict): The template containing the sparqlTemplate

        Returns:
            dict: Selected entity info or None if not found
        """
        sparql_template = template["sparqlTemplate"]

        # Extract the predicate pattern for the entity
        # Look for patterns like: {entity} predicate ?object
        predicate_match = re.search(r"{entity}\s+([^\s.{}<>]+)\s+", sparql_template)

        if not predicate_match:
            # Try the inverse pattern: ?subject predicate {entity}
            predicate_match = re.search(r"([^\s.{}<>]+)\s+{entity}", sparql_template)
            if predicate_match:
                # This is an inverse relationship - not implemented yet
                return None

        if not predicate_match:
            return None

        predicate = predicate_match.group(1)

        # Handle RDF/SPARQL prefixes
        if ":" in predicate:
            prefix, local_name = predicate.split(":", 1)
            if prefix in self.prefixes:
                predicate_uri = f"{self.prefixes[prefix]}{local_name}"
            else:
                # Unknown prefix, can't construct URI
                return None
        else:
            # Not a prefixed name, use as is
            predicate_uri = predicate

        # Create the query to find valid subjects for this predicate
        query = f"""
            SELECT DISTINCT ?entity ?label
            WHERE {{
                ?entity <{predicate_uri}> ?obj .
                OPTIONAL {{ ?entity rdfs:label ?label }}
            }}
        """

        try:
            # Execute query against the endpoint
            results = self.sparql_exec.execute_query(query)

            if not results:
                return None

            # Randomly select one entity from the results
            selected = random.choice(results)
            entity_uri = selected["entity"]

            # Use label if available, otherwise extract from URI
            if "label" in selected and selected["label"]:
                entity_label = selected["label"]
            else:
                entity_label = self.extract_label_from_uri(entity_uri)

            return {
                "value": self.shorten_uri(entity_uri),
                "label": entity_label,
                "uri": entity_uri,
            }

        except Exception as e:
            print(f"Error selecting entity from endpoint: {e}")
            print(query)
            return None

    def select_value_from_endpoint(self, template, placeholder):
        """
        Select a value from the SPARQL endpoint that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            placeholder (str): The name of the placeholder
            
        Returns:
            dict: Selected value info or None if not found
        """
        sparql_template = template["sparqlTemplate"]
        
        # Extract the predicate pattern for the value
        # Look for patterns like: ?subject predicate {value}
        predicate_match = re.search(r'([^\s.{}<>]+)\s+' + re.escape('{' + placeholder + '}'), sparql_template)
        
        if not predicate_match:
            # Try alternative pattern: FILTER(something({value}))
            # This is more complex and would need special handling for each case
            
            # For year values in the laws-enacted-in-year template
            if "laws-enacted-in-year" in template["id"]:
                # Extract a list of years from the endpoint
                query = """
                    SELECT DISTINCT ?year
                    WHERE {
                        ?law <https://example.org/lex2kg/ontology/tahun> ?year .
                    }
                    ORDER BY ?year
                """
                
                try:
                    results = self.sparql_exec.execute_query(query)
                    if results:
                        # Pick a random year from results
                        year_value = str(random.choice(results)["year"])
                        return {
                            "value": year_value,
                            "label": year_value
                        }
                except Exception as e:
                    print(f"Error querying for years: {e}")
            
            # For enactor names in law-by-enactor template
            elif "law-by-enactor" in template["id"]:
                query = """
                    SELECT DISTINCT ?enactor
                    WHERE {
                        ?law <https://example.org/lex2kg/ontology/disahkanOleh> ?enactor .
                    }
                """
                
                try:
                    results = self.sparql_exec.execute_query(query)
                    if results:
                        # Pick a random enactor
                        enactor = str(random.choice(results)["enactor"])
                        return {
                            "value": enactor,
                            "label": enactor,
                            "sparqlValue": f'"{enactor}"'  # Add quotes for the SPARQL query
                        }
                except Exception as e:
                    print(f"Error querying for enactors: {e}")
            
            # For keywords in law-by-keyword template
            elif "law-by-keyword" in template["id"]:
                # Use our pre-extracted keywords
                return self.select_keyword_value()
            
            return None
        
        predicate = predicate_match.group(1)
        
        # Handle RDF/SPARQL prefixes
        if ':' in predicate:
            prefix, local_name = predicate.split(':', 1)
            if prefix in self.prefixes:
                predicate_uri = f"{self.prefixes[prefix]}{local_name}"
            else:
                # Unknown prefix, can't construct URI
                return None
        else:
            # Not a prefixed name, use as is
            predicate_uri = predicate
            
        # Create the query to find valid values for this predicate
        query = f"""
            SELECT DISTINCT ?value
            WHERE {{
                ?subject <{predicate_uri}> ?value .
            }}
        """
        
        try:
            # Execute query against the endpoint
            results = self.sparql_exec.execute_query(query)
            
            if not results:
                return None
                
            # Randomly select one value from the results
            selected_value = random.choice(results)["value"]
            value_str = str(selected_value)
            
            # Check if the value looks like a URI
            if value_str.startswith("http"):
                return {
                    "value": self.shorten_uri(value_str),
                    "label": self.extract_label_from_uri(value_str),
                    "uri": value_str
                }
            
            # Check if the value looks like a number
            try:
                float(value_str)  # Test if it can be converted to a number
                return {
                    "value": value_str,
                    "label": value_str
                }
            except ValueError:
                # It's a string value, add quotes for SPARQL
                return {
                    "value": value_str,
                    "label": value_str,
                    "sparqlValue": f'"{value_str}"'  # Add quotes for strings
                }
                
        except Exception as e:
            print(f"Error selecting value from endpoint: {e}")
            return None

    def select_entity_by_pattern(self, pattern):
        """
        Select a random entity that matches a URI pattern

        Args:
            pattern (str): Pattern to match in entity URI

        Returns:
            dict: Selected entity or None
        """
        # Filter entities by URI pattern
        matching_entities = [
            e for e in self.entity_examples if pattern in e.get("uri", "")
        ]

        if matching_entities:
            return random.choice(matching_entities)

        return None

    def select_random_entity(self):
        """
        Select a random entity from available examples

        Returns:
            dict: Selected entity
        """
        # If we have entity examples from the schema extractor, use them
        if self.entity_examples:
            return random.choice(self.entity_examples)

        # Fallback to predefined legal entities
        # This ensures we always have something workable for the legal data
        legal_entities = [
            {
                "value": "lex2kg-o:UU-2020-9",
                "label": "UU No. 9 Tahun 2020",
                "uri": "https://example.org/lex2kg/uu/2020/9",
                "type": "lex2kg-o:UndangUndang",
            },
            {
                "value": "lex2kg-o:UU-2020-11",
                "label": "UU No. 11 Tahun 2020",
                "uri": "https://example.org/lex2kg/uu/2020/11",
                "type": "lex2kg-o:UndangUndang",
            },
            {
                "value": "lex2kg-o:UU-2020-9-pasal-47",
                "label": "Pasal 47 UU No. 9 Tahun 2020",
                "uri": "https://example.org/lex2kg/uu/2020/9/pasal/0047",
                "type": "lex2kg-o:Pasal",
            },
            {
                "value": "lex2kg-o:UU-2020-11-bab-10",
                "label": "Bab 10 UU No. 11 Tahun 2020",
                "uri": "https://example.org/lex2kg/uu/2020/11/bab/0010",
                "type": "lex2kg-o:Bab",
            },
            {
                "value": "lex2kg-o:UU-2020-9-pasal-46-ayat-1",
                "label": "Pasal 46 Ayat 1 UU No. 9 Tahun 2020",
                "uri": "https://example.org/lex2kg/uu/2020/9/pasal/0046/versi/20201026/ayat/0001",
                "type": "lex2kg-o:Ayat",
            },
        ]

        print("Warning: Using fallback legal entities")
        return random.choice(legal_entities)

    def select_legal_property(self, template, placeholder):
        """
        Select a property appropriate for legal templates

        Args:
            template (dict): The template being instantiated
            placeholder (str): The property placeholder name

        Returns:
            dict: Selected property
        """
        # Define common legal properties
        legal_properties = {
            "title": {
                "value": "lex2kg-o:tentang",
                "label": "tentang",
                "uri": "https://example.org/lex2kg/ontology/tentang",
            },
            "enactment_date": {
                "value": "lex2kg-o:disahkanPada",
                "label": "disahkan pada",
                "uri": "https://example.org/lex2kg/ontology/disahkanPada",
            },
            "enactment_location": {
                "value": "lex2kg-o:disahkanDi",
                "label": "disahkan di",
                "uri": "https://example.org/lex2kg/ontology/disahkanDi",
            },
            "enactor": {
                "value": "lex2kg-o:disahkanOleh",
                "label": "disahkan oleh",
                "uri": "https://example.org/lex2kg/ontology/disahkanOleh",
            },
            "enactor_position": {
                "value": "lex2kg-o:jabatanPengesah",
                "label": "jabatan pengesah",
                "uri": "https://example.org/lex2kg/ontology/jabatanPengesah",
            },
            "regulation_type": {
                "value": "lex2kg-o:jenisPeraturan",
                "label": "jenis peraturan",
                "uri": "https://example.org/lex2kg/ontology/jenisPeraturan",
            },
            "content": {
                "value": "lex2kg-o:teks",
                "label": "teks",
                "uri": "https://example.org/lex2kg/ontology/teks",
            },
            "chapter_title": {
                "value": "lex2kg-o:judul",
                "label": "judul",
                "uri": "https://example.org/lex2kg/ontology/judul",
            },
        }

        # First check if our schema info has this property
        if "properties" in self.schema_info:
            # Try to find a matching property from the schema
            if "title" in template["id"] or "title" in placeholder:
                prop = self.find_property_by_name(
                    "tentang"
                ) or self.find_property_by_name("judul")
                if prop:
                    return prop

            elif "enactment-date" in template["id"] or "date" in placeholder:
                prop = self.find_property_by_name("disahkanPada")
                if prop:
                    return prop

            elif "enactment-location" in template["id"] or "location" in placeholder:
                prop = self.find_property_by_name("disahkanDi")
                if prop:
                    return prop

            elif "enactment-person" in template["id"] or "person" in placeholder:
                prop = self.find_property_by_name("disahkanOleh")
                if prop:
                    return prop

            elif "enactment-position" in template["id"] or "position" in placeholder:
                prop = self.find_property_by_name("jabatanPengesah")
                if prop:
                    return prop

            elif "type" in template["id"] or "type" in placeholder:
                prop = self.find_property_by_name("jenisPeraturan")
                if prop:
                    return prop

            elif "text" in template["id"] or "content" in placeholder:
                prop = self.find_property_by_name("teks")
                if prop:
                    return prop

        # If we don't have the property in schema info, use our predefined ones
        if "title" in template["id"] or "title" in placeholder:
            if "chapter" in template["id"]:
                return legal_properties["chapter_title"]
            else:
                return legal_properties["title"]

        elif "enactment-date" in template["id"] or "date" in placeholder:
            return legal_properties["enactment_date"]

        elif "enactment-location" in template["id"] or "location" in placeholder:
            return legal_properties["enactment_location"]

        elif "enactment-person" in template["id"] or "person" in placeholder:
            return legal_properties["enactor"]

        elif "enactment-position" in template["id"] or "position" in placeholder:
            return legal_properties["enactor_position"]

        elif "type" in template["id"] or "type" in placeholder:
            return legal_properties["regulation_type"]

        elif "text" in template["id"] or "content" in placeholder:
            return legal_properties["content"]

        # Fallback to any property if we can't find a specific match
        if "properties" in self.schema_info and self.schema_info["properties"]:
            return random.choice(self.schema_info["properties"])

        # Last resort - return title as default
        return legal_properties["title"]

    def select_enactor_value(self):
        """
        Select a realistic enactor value for legal documents

        Returns:
            dict: Enactor value object
        """
        enactors = [
            "JOKO WIDODO",
            "SUSILO BAMBANG YUDHOYONO",
            "MEGAWATI SOEKARNOPUTRI",
            "ABDURRAHMAN WAHID",
            "SOEHARTO",
            "BACHARUDDIN JUSUF HABIBIE",
        ]
        value = random.choice(enactors)
        return {"value": value, "label": value, "sparqlValue": f'"{value}"'}

    def select_year_value(self):
        """
        Select a realistic year value for legal documents

        Returns:
            dict: Year value object
        """
        years = list(range(1990, 2021))
        value = random.choice(years)
        return {"value": str(value), "label": str(value)}

    def select_keyword_value(self):
        """
        Select a keyword value for searching legal documents

        Returns:
            dict: Keyword value object
        """
        # Use the pre-extracted keywords if available
        if self.extracted_keywords:
            value = random.choice(self.extracted_keywords)
        else:
            # Fallback to predefined keywords
            print("Using fallback keywords")
            value = random.choice(self.fallback_keywords)

        return {"value": value, "label": value, "sparqlValue": f'"{value}"'}

    def select_random_value(self, template):
        """
        Select a random appropriate value

        Args:
            template (dict): The template being instantiated

        Returns:
            dict: Selected value
        """
        # Special handling for legal data
        if template.get("category") == "legal":
            if "law-by-enactor" in template["id"]:
                return self.select_enactor_value()
            elif "laws-enacted-in-year" in template["id"]:
                return self.select_year_value()
            elif "law-by-keyword" in template["id"]:
                return self.select_keyword_value()

        # Default to a generic value
        dummy_value = random.randint(1, 10)
        return {"value": str(dummy_value), "label": str(dummy_value)}

    def find_property_by_name(self, name):
        """
        Find a property by name in schema info

        Args:
            name (str): Property name to find

        Returns:
            dict: Found property or None
        """
        if "properties" not in self.schema_info:
            return None

        for prop in self.schema_info["properties"]:
            if (
                name in prop["value"]
                or name in prop["label"]
                or (prop.get("uri", "").split("/")[-1] == name)
            ):
                return prop

        return None

    def extract_label_from_uri(self, uri):
        """
        Extract a human-readable label from a URI

        Args:
            uri (str): URI to extract label from

        Returns:
            str: Human-readable label
        """
        return legal_entity_label(uri)

    def shorten_uri(self, uri):
        """
        Shorten a URI using known prefixes

        Args:
            uri (str): URI to shorten

        Returns:
            str: Shortened URI
        """
        for prefix, namespace in self.prefixes.items():
            if uri.startswith(namespace):
                return f"{prefix}:{uri[len(namespace):]}"

        return uri

    def format_sparql(self, sparql):
        """
        Format SPARQL query for readability with properly formatted URIs

        Args:
            sparql (str): Raw SPARQL query

        Returns:
            str: Formatted SPARQL query
        """

        # First, clean URIs by removing spaces within angle brackets
        def clean_uri(match):
            uri = match.group(0)
            # Remove all spaces from URIs
            return uri.replace(" ", "")

        # Fix all URIs first by removing spaces
        sparql = re.sub(r"<[^>]+>", clean_uri, sparql)

        # Now proceed with other formatting
        sparql = re.sub(r"PREFIX\s+\w+:\s+<[^>]+>\s*", "", sparql)
        sparql = re.sub(r"\s+", " ", sparql)

        # Format spaces around keywords properly
        sparql = re.sub(r"(?i)\bSELECT\b", "select", sparql)
        sparql = re.sub(r"(?i)\bWHERE\b", " where ", sparql)
        sparql = re.sub(r"(?i)\bFILTER\b", " filter ", sparql)
        sparql = re.sub(r"(?i)\bORDER BY\b", " order by ", sparql)
        sparql = re.sub(r"(?i)\bLIMIT\b", " limit ", sparql)
        sparql = re.sub(r"(?i)\bGROUP BY\b", " group by ", sparql)
        sparql = re.sub(r"(?i)\bHAVING\b", " having ", sparql)
        sparql = re.sub(r"(?i)\bCOUNT\b", "count", sparql)
        sparql = re.sub(r"(?i)\bAS\b", " as ", sparql)
        sparql = re.sub(r"(?i)\bDISTINCT\b", "distinct ", sparql)

        # Format braces
        sparql = re.sub(r"\s*{\s*", " { ", sparql)
        sparql = re.sub(r"\s*}\s*", " } ", sparql)

        # Fix the dot spacing - NO SPACES around dots
        # sparql = re.sub(r'\s*\.\s*', '.', sparql)

        # Final cleanup of any double spaces
        sparql = re.sub(r"\s+", " ", sparql).strip()

        return sparql

    def export_json(self, dataset):
        """
        Export dataset to JSON format

        Args:
            dataset (list): Generated dataset

        Returns:
            str: JSON string
        """
        return json.dumps(dataset, indent=2)

    def export_csv(self, dataset):
        """
        Export dataset to CSV format

        Args:
            dataset (list): Generated dataset

        Returns:
            str: CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Write header
        writer.writerow(
            [
                "id",
                "question",
                "englishQuestion",
                "sparql",
                "category",
                "complexity",
                "templateId",
            ]
        )

        # Write rows
        for item in dataset:
            sparql_escaped = item["sparql"].replace("\n", " ")
            writer.writerow(
                [
                    item["id"],
                    item["question"],
                    item["englishQuestion"],
                    sparql_escaped,
                    item["category"],
                    item["complexity"],
                    item["templateId"],
                ]
            )

        return output.getvalue()

    def export_jsonl(self, dataset):
        """
        Export dataset to JSONL format (one JSON object per line)

        Args:
            dataset (list): Generated dataset

        Returns:
            str: JSONL string
        """
        return "\n".join(json.dumps(item) for item in dataset)
