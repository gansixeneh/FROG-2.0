"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator - Modified for Fuseki Server

This version supports context-aware entity selection, generating queries with real entities from
the knowledge graph that match the template structure using a discovery-based approach.
Enhanced with chain of thoughts and entity/property matching similar to the curi approach.
"""

import json
import random
import re
import datetime
import csv
import io
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import Counter
from kg_schema_extractor import legal_entity_label, legal_property_label
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams


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
        self, 
        config, 
        endpoint_url="http://localhost:3030/modified-lex2kg/query",
        property_retrieval=None
    ):
        """
        Initialize the generator with knowledge graph schema information

        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
            endpoint_url (str): URL of the Fuseki SPARQL endpoint
            property_retrieval: Property retrieval system for Weaviate-based search
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.variation_generator = VariationGenerator()
        self.property_retrieval = property_retrieval

        # Initialize stopwords
        self.stopwords = set(stopwords.words('english'))

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
        Initialize question-query template pairs for legal document data
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # Legal document specific templates
        legal_templates = [
            # Basic information about laws (UU)
            {
                "id": "law-title",
                "category": "legal",
                "questionTemplates": [
                    "Apa judul dari {entity}?",
                    "Apa nama dari {entity}?", 
                    "Bagaimana judul dari {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the title of {entity}?",
                    "What is the name of {entity}?",
                    "How is the title of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    {entity} lex2kg-o:tentang ?title .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the title of {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:tentang' links a legal document to its title or subject matter.",
                    "4. To solve this, retrieve the title linked to {entity} via the 'lex2kg-o:tentang' property.",
                    "5. Construct a SPARQL query to retrieve the title for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "law-enactment-date",
                "category": "legal",
                "questionTemplates": [
                    "Kapan {entity} disahkan?",
                    "Pada tanggal berapa {entity} disahkan?",
                    "Tanggal berapa {entity} disahkan?"
                ],
                "englishQuestionTemplates": [
                    "When was {entity} enacted?",
                    "On what date was {entity} enacted?",
                    "What date was {entity} enacted?"
                ],
                "sparqlTemplate": """
                    SELECT ?date WHERE {
                    {entity} lex2kg-o:disahkanPada ?date .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the enactment date of {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:disahkanPada' links a legal document to its enactment date.",
                    "4. To solve this, retrieve the date linked to {entity} via the 'lex2kg-o:disahkanPada' property.",
                    "5. Construct a SPARQL query to retrieve the enactment date for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "law-enactment-location",
                "category": "legal",
                "questionTemplates": [
                    "Di mana {entity} disahkan?",
                    "Di kota mana {entity} disahkan?",
                    "Di tempat mana {entity} disahkan?"
                ],
                "englishQuestionTemplates": [
                    "Where was {entity} enacted?",
                    "In which city was {entity} enacted?",
                    "In what place was {entity} enacted?"
                ],
                "sparqlTemplate": """
                    SELECT ?location WHERE {
                    {entity} lex2kg-o:disahkanDi ?location .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the enactment location of {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:disahkanDi' links a legal document to its enactment location.",
                    "4. To solve this, retrieve the location linked to {entity} via the 'lex2kg-o:disahkanDi' property.",
                    "5. Construct a SPARQL query to retrieve the enactment location for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "law-enactment-person",
                "category": "legal",
                "questionTemplates": [
                    "Siapa yang mengesahkan {entity}?",
                    "Siapa nama orang yang mengesahkan {entity}?",
                    "Oleh siapa {entity} disahkan?"
                ],
                "englishQuestionTemplates": [
                    "Who enacted {entity}?",
                    "What is the name of the person who enacted {entity}?",
                    "By whom was {entity} signed?"
                ],
                "sparqlTemplate": """
                    SELECT ?person WHERE {
                    {entity} lex2kg-o:disahkanOleh ?person .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the person who enacted {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:disahkanOleh' links a legal document to the person who enacted it.",
                    "4. To solve this, retrieve the person linked to {entity} via the 'lex2kg-o:disahkanOleh' property.",
                    "5. Construct a SPARQL query to retrieve the enacting person for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "law-enactment-position",
                "category": "legal",
                "questionTemplates": [
                    "Apa jabatan pengesah {entity}?",
                    "Apa posisi pengesah {entity}?",
                    "Jabatan apa yang dimiliki oleh pengesah {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the position of the person who enacted {entity}?",
                    "What is the role of the person who enacted {entity}?",
                    "What position does the enactor of {entity} hold?"
                ],
                "sparqlTemplate": """
                    SELECT ?position WHERE {
                    {entity} lex2kg-o:jabatanPengesah ?position .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the position of the person who enacted {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:jabatanPengesah' links a legal document to the position of its enactor.",
                    "4. To solve this, retrieve the position linked to {entity} via the 'lex2kg-o:jabatanPengesah' property.",
                    "5. Construct a SPARQL query to retrieve the enactor's position for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "law-type",
                "category": "legal",
                "questionTemplates": [
                    "Apa jenis peraturan dari {entity}?",
                    "Apa kategori peraturan dari {entity}?",
                    "Termasuk jenis peraturan apa {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What type of regulation is {entity}?",
                    "What category of regulation is {entity}?",
                    "Which type of regulation is {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?type WHERE {
                    {entity} lex2kg-o:jenisPeraturan ?type .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the regulation type of {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:jenisPeraturan' links a legal document to its regulation type.",
                    "4. To solve this, retrieve the type linked to {entity} via the 'lex2kg-o:jenisPeraturan' property.",
                    "5. Construct a SPARQL query to retrieve the regulation type for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "article-text",
                "category": "legal",
                "questionTemplates": [
                    "Apa isi dari {entity}?",
                    "Apa konten dari {entity}?",
                    "Bagaimana bunyi dari {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the content of {entity}?",
                    "What is the text of {entity}?",
                    "How does the text read for {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?text WHERE {
                    {entity} lex2kg-o:teks ?text .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the text content of {entity}.",
                    "2. The entity '{entity}' represents a legal article or section in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:teks' links a legal article to its actual text content.",
                    "4. To solve this, retrieve the text linked to {entity} via the 'lex2kg-o:teks' property.",
                    "5. Construct a SPARQL query to retrieve the text content for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "article-version",
                "category": "legal",
                "questionTemplates": [
                    "Apa versi terbaru dari {entity}?",
                    "Versi terbaru apa dari {entity}?",
                    "Bagaimana versi terkini dari {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the latest version of {entity}?",
                    "What latest version of {entity} exists?",
                    "How is the current version of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?version WHERE {
                    {entity} lex2kg-o:versi ?version .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the latest version of {entity}.",
                    "2. The entity '{entity}' represents a legal article or document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:versi' links a legal document to its version information.",
                    "4. To solve this, retrieve the version linked to {entity} via the 'lex2kg-o:versi' property.",
                    "5. Construct a SPARQL query to retrieve the version for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "chapter-title",
                "category": "legal",
                "questionTemplates": [
                    "Apa judul dari {entity}?",
                    "Apa nama dari {entity}?",
                    "Bagaimana judul dari {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the title of {entity}?",
                    "What is the name of {entity}?",
                    "How is the title of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    {entity} lex2kg-o:judul ?title .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the title of {entity}.",
                    "2. The entity '{entity}' represents a chapter (bab) in a legal document.",
                    "3. The property 'lex2kg-o:judul' links a chapter to its title.",
                    "4. To solve this, retrieve the title linked to {entity} via the 'lex2kg-o:judul' property.",
                    "5. Construct a SPARQL query to retrieve the title for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "law-language",
                "category": "legal",
                "questionTemplates": [
                    "Dalam bahasa apa {entity} ditulis?",
                    "Bahasa apa yang digunakan dalam {entity}?",
                    "Apa bahasa penulisan {entity}?"
                ],
                "englishQuestionTemplates": [
                    "In what language is {entity} written?",
                    "What language is used in {entity}?",
                    "What is the writing language of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?language WHERE {
                    {entity} lex2kg-o:bahasa ?language .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the language in which {entity} is written.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:bahasa' links a legal document to its language.",
                    "4. To solve this, retrieve the language linked to {entity} via the 'lex2kg-o:bahasa' property.",
                    "5. Construct a SPARQL query to retrieve the language for {entity}."
                ],
                "complexity": "basic"
            },
            
            # Intermediate: Structure and relationships
            {
                "id": "law-articles-count",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah pasal dalam {entity}?",
                    "Ada berapa pasal dalam {entity}?",
                    "Jumlah pasal dalam {entity} ada berapa?"
                ],
                "englishQuestionTemplates": [
                    "How many articles are in {entity}?",
                    "What is the number of articles in {entity}?",
                    "How many articles does {entity} contain?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?article) AS ?count) WHERE {
                    {entity} lex2kg-o:pasal ?article .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of articles (pasal) in {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:pasal' links a legal document to its articles.",
                    "4. To solve this, count all articles linked to {entity} via the 'lex2kg-o:pasal' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the total number of articles."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "law-chapters-count",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah bab dalam {entity}?",
                    "Ada berapa bab dalam {entity}?",
                    "Jumlah bab dalam {entity} ada berapa?"
                ],
                "englishQuestionTemplates": [
                    "How many chapters are in {entity}?",
                    "What is the number of chapters in {entity}?",
                    "How many chapters does {entity} contain?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?chapter) AS ?count) WHERE {
                    {entity} lex2kg-o:bab ?chapter .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of chapters (bab) in {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:bab' links a legal document to its chapters.",
                    "4. To solve this, count all chapters linked to {entity} via the 'lex2kg-o:bab' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the total number of chapters."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "article-sections-count",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah ayat dalam {entity}?",
                    "Ada berapa ayat dalam {entity}?",
                    "Jumlah ayat dalam {entity} ada berapa?"
                ],
                "englishQuestionTemplates": [
                    "How many sections are in {entity}?",
                    "What is the number of sections in {entity}?",
                    "How many sections does {entity} contain?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?section) AS ?count) WHERE {
                    {entity} lex2kg-o:ayat ?section .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of sections (ayat) in {entity}.",
                    "2. The entity '{entity}' represents an article in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:ayat' links an article to its sections.",
                    "4. To solve this, count all sections linked to {entity} via the 'lex2kg-o:ayat' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the total number of sections."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "article-reference",
                "category": "legal",
                "questionTemplates": [
                    "Pasal-pasal mana yang merujuk ke {entity}?",
                    "Pasal apa saja yang merujuk ke {entity}?",
                    "Rujukan ke {entity} ada di pasal mana saja?"
                ],
                "englishQuestionTemplates": [
                    "Which articles reference {entity}?",
                    "What articles refer to {entity}?",
                    "Where are references to {entity} found in articles?"
                ],
                "sparqlTemplate": """
                    SELECT ?referringArticle WHERE {
                    ?textSegment lex2kg-o:merujuk {entity} .
                    ?referringArticle lex2kg-o:versi ?textSegment .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for articles that reference {entity}.",
                    "2. The entity '{entity}' represents a legal element in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:merujuk' links text segments to what they reference.",
                    "4. The property 'lex2kg-o:versi' links articles to their text segments or versions.",
                    "5. To solve this, find text segments that reference {entity}, then find articles that have those segments.",
                    "6. Construct a SPARQL query with a join pattern to retrieve the referring articles."
                ],
                "complexity": "advanced"
            },
            {
                "id": "latest-law-in-year",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang terakhir yang disahkan pada tahun {value}?",
                    "Peraturan terakhir yang disahkan di tahun {value}?",
                    "Apa UU terakhir yang disahkan tahun {value}?"
                ],
                "englishQuestionTemplates": [
                    "What was the latest law enacted in the year {value}?",
                    "What was the last regulation passed in {value}?",
                    "Which law was enacted last in {value}?"
                ],
                "sparqlTemplate": """
                    SELECT ?law WHERE {
                    ?law lex2kg-o:tahun {value} .
                    ?law lex2kg-o:disahkanPada ?date .
                    }
                    ORDER BY DESC(?date)
                    LIMIT 1
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the latest law enacted in the year {value}.",
                    "2. The property 'lex2kg-o:tahun' links laws to their year.",
                    "3. The property 'lex2kg-o:disahkanPada' links laws to their enactment dates.",
                    "4. To solve this, find laws from the year {value}, then order them by date in descending order.",
                    "5. Construct a SPARQL query with ORDER BY DESC and LIMIT 1 to get the latest law from that year."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "paragraph-count",
                "category": "legal",
                "questionTemplates": [
                    "Berapa jumlah paragraf dalam bagian {entity}?",
                    "Ada berapa paragraf dalam bagian {entity}?",
                    "Jumlah paragraf dalam bagian {entity} ada berapa?"
                ],
                "englishQuestionTemplates": [
                    "How many paragraphs are in section {entity}?",
                    "What is the number of paragraphs in section {entity}?",
                    "How many paragraphs does section {entity} contain?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?paragraph) AS ?count) WHERE {
                    {entity} lex2kg-o:paragraf ?paragraph .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of paragraphs in {entity}.",
                    "2. The entity '{entity}' represents a section in a legal document.",
                    "3. The property 'lex2kg-o:paragraf' links a section to its paragraphs.",
                    "4. To solve this, count all paragraphs linked to {entity} via the 'lex2kg-o:paragraf' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the total number of paragraphs."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "specific-year-law-count",
                "category": "legal",
                "questionTemplates": [
                    "Berapa undang-undang yang disahkan pada tahun {value}?",
                    "Ada berapa undang-undang yang disahkan tahun {value}?",
                    "Jumlah undang-undang yang disahkan tahun {value} ada berapa?"
                ],
                "englishQuestionTemplates": [
                    "How many laws were enacted in the year {value}?",
                    "What is the number of laws passed in {value}?",
                    "How many laws were passed during {value}?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?law) AS ?count) WHERE {
                    ?law lex2kg-o:tahun {value} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of laws enacted in the year {value}.",
                    "2. The property 'lex2kg-o:tahun' links laws to their year of enactment.",
                    "3. To solve this, count all laws linked to the year {value} via the 'lex2kg-o:tahun' property.",
                    "4. Construct a SPARQL query using the COUNT function to determine the total number of laws from that year."
                ],
                "complexity": "intermediate"
            },
            
            # Advanced: Complex relationships and analytics
            {
                "id": "law-amended-by",
                "category": "legal",
                "questionTemplates": [
                    "Pasal-pasal mana yang mengubah {entity}?",
                    "Pasal apa saja yang mengubah {entity}?",
                    "Perubahan terhadap {entity} terdapat di pasal mana?"
                ],
                "englishQuestionTemplates": [
                    "Which law amended {entity}?",
                    "What laws made changes to {entity}?",
                    "Where are amendments to {entity} found?"
                ],
                "sparqlTemplate": """
                    SELECT ?amendment WHERE {
                    ?letter lex2kg-o:mengubah {entity} .
                    ?version lex2kg-o:huruf ?letter .
                    ?amendment lex2kg-o:versi ?version .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for amendments that modified {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:mengubah' links amendment letters to what they modify.",
                    "4. The property 'lex2kg-o:huruf' links versions to their letters.",
                    "5. The property 'lex2kg-o:versi' links amendments to their versions.",
                    "6. To solve this, trace the connection from letters that modify {entity} to the amendments they belong to.",
                    "7. Construct a SPARQL query with a complex join pattern to retrieve the amendments to {entity}."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "law-amendment",
                "category": "legal",
                "questionTemplates": [
                    "Pasal-pasal apa saja yang diubah oleh {entity}?",
                    "Pasal mana saja yang diamendemen oleh {entity}?",
                    "Apa saja pasal yang mengalami perubahan oleh {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Which laws were amended by {entity}?",
                    "What articles were changed by {entity}?",
                    "Which sections underwent modifications by {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?amendedLaw WHERE {
                        {entity} lex2kg-o:pasal ?article .
                        ?article lex2kg-o:versi ?articleVersion .
                        ?articleVersion lex2kg-o:huruf ?letter .
                        ?letter lex2kg-o:mengubah ?amendedArticleVersion .
                        ?amendedArticle lex2kg-o:versi ?amendedArticleVersion .
                        ?amendedLaw lex2kg-o:pasal ?amendedArticle .
                        ?amendedLaw a lex2kg-o:Peraturan
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for legal articles that were amended by {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:pasal' links laws to their articles.",
                    "4. The property 'lex2kg-o:versi' links articles to their versions.",
                    "5. The property 'lex2kg-o:huruf' links versions to their letters.",
                    "6. The property 'lex2kg-o:mengubah' links letters to the versions they modify.",
                    "7. To solve this, trace the complex connection path from {entity} to laws it amended.",
                    "8. Construct a SPARQL query with multiple joins to find the amended laws."
                ],
                "complexity": "advanced"
            },
            {
                "id": "law-by-keyword",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang apa saja yang berhubungan dengan '{value}'?",
                    "Peraturan apa saja yang terkait dengan '{value}'?",
                    "Regulasi mana yang membahas tentang '{value}'?"
                ],
                "englishQuestionTemplates": [
                    "Which laws are related to '{value}'?",
                    "What regulations are associated with '{value}'?",
                    "Which legal documents discuss '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?law WHERE {
                    ?law lex2kg-o:tentang ?title .
                    FILTER(CONTAINS(LCASE(?title), LCASE({value})))
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for laws related to the keyword '{value}'.",
                    "2. The property 'lex2kg-o:tentang' links laws to their titles or subject matter.",
                    "3. To solve this, find laws whose titles contain the keyword '{value}'.",
                    "4. Construct a SPARQL query using FILTER with CONTAINS to match laws with titles containing '{value}'.",
                    "5. Use LCASE to make the search case-insensitive."
                ],
                "complexity": "advanced"
            },
            {
                "id": "law-with-most-articles",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang dengan jumlah pasal terbanyak?",
                    "Peraturan mana yang memiliki pasal terbanyak?",
                    "UU dengan jumlah pasal paling banyak?"
                ],
                "englishQuestionTemplates": [
                    "Which law has the most articles?",
                    "What regulation contains the highest number of articles?",
                    "Which legal document has the largest article count?"
                ],
                "sparqlTemplate": """
                    SELECT ?law WHERE {
                    ?law lex2kg-o:pasal ?article .
                    }
                    GROUP BY ?law
                    ORDER BY DESC(COUNT(?article))
                    LIMIT 1
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the law with the most articles.",
                    "2. The property 'lex2kg-o:pasal' links laws to their articles.",
                    "3. To solve this, count the articles for each law, then find the law with the highest count.",
                    "4. Construct a SPARQL query using GROUP BY to group by law.",
                    "5. Use ORDER BY DESC with COUNT to sort laws by their article count in descending order.",
                    "6. Use LIMIT 1 to get only the law with the highest count."
                ],
                "complexity": "advanced"
            },
            {
                "id": "law-by-enactor",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang terbaru yang disahkan oleh {value}?",
                    "Peraturan terkini yang ditandatangani oleh {value}?",
                    "UU terakhir yang disahkan oleh {value}?"
                ],
                "englishQuestionTemplates": [
                    "What is the most recent law enacted by {value}?",
                    "What is the latest regulation signed by {value}?",
                    "Which was the last law passed by {value}?"
                ],
                "sparqlTemplate": """
                    SELECT ?law WHERE {
                    ?law lex2kg-o:disahkanOleh {value} .
                    ?law lex2kg-o:disahkanPada ?date .
                    }
                    ORDER BY DESC(?date)
                    LIMIT 1
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the most recent law enacted by {value}.",
                    "2. The property 'lex2kg-o:disahkanOleh' links laws to their enactors.",
                    "3. The property 'lex2kg-o:disahkanPada' links laws to their enactment dates.",
                    "4. To solve this, find laws enacted by {value}, then order them by date in descending order.",
                    "5. Construct a SPARQL query with ORDER BY DESC and LIMIT 1 to get the most recent law."
                ],
                "complexity": "advanced"
            },
            {
                "id": "law-deletion",
                "category": "legal",
                "questionTemplates": [
                    "Apa saja pasal yang dihapus oleh {entity}?",
                    "Pasal mana saja yang dihapuskan oleh {entity}?",
                    "Bagian mana yang dihilangkan oleh {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Which articles were deleted by {entity}?",
                    "What sections were removed by {entity}?",
                    "Which parts were eliminated by {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?deletedArticle WHERE {
                    {entity} lex2kg-o:menghapus ?deletedArticle .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for articles that were deleted by {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:menghapus' links laws to articles they deleted.",
                    "4. To solve this, retrieve all articles linked to {entity} via the 'lex2kg-o:menghapus' property.",
                    "5. Construct a SPARQL query to list all deleted articles."
                ],
                "complexity": "advanced"
            },
            {
                "id": "law-insertion",
                "category": "legal",
                "questionTemplates": [
                    "Apa saja pasal yang disisipkan oleh {entity}?",
                    "Pasal mana saja yang ditambahkan oleh {entity}?",
                    "Bagian baru apa yang dimasukkan oleh {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Which articles were inserted by {entity}?",
                    "What sections were added by {entity}?",
                    "Which new parts were introduced by {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?insertedArticle WHERE {
                    {entity} lex2kg-o:menyisipkan ?insertedArticle .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for articles that were inserted by {entity}.",
                    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",
                    "3. The property 'lex2kg-o:menyisipkan' links laws to articles they inserted.",
                    "4. To solve this, retrieve all articles linked to {entity} via the 'lex2kg-o:menyisipkan' property.",
                    "5. Construct a SPARQL query to list all inserted articles."
                ],
                "complexity": "advanced"
            },
            {
                "id": "oldest-law",
                "category": "legal",
                "questionTemplates": [
                    "Undang-undang tertua dalam sistem?",
                    "Peraturan paling lama dalam database?",
                    "UU dengan tanggal paling awal dalam sistem?"
                ],
                "englishQuestionTemplates": [
                    "What is the oldest law in the system?",
                    "Which is the earliest regulation in the database?",
                    "What is the first law recorded in the system?"
                ],
                "sparqlTemplate": """
                    SELECT ?law WHERE {
                    ?law lex2kg-o:disahkanPada ?date .
                    ?law lex2kg-o:jenisPeraturan ?type .
                    FILTER(?type = <https://example.org/lex2kg/ontology/jenisPeraturan/UU>)
                    }
                    ORDER BY ?date
                    LIMIT 1
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the oldest law in the system.",
                    "2. The property 'lex2kg-o:disahkanPada' links laws to their enactment dates.",
                    "3. The property 'lex2kg-o:jenisPeraturan' identifies the type of regulation.",
                    "4. To solve this, find laws of type UU, then order them by date in ascending order.",
                    "5. Construct a SPARQL query with FILTER to restrict to laws (UU), ORDER BY for date, and LIMIT 1 to get the oldest."
                ],
                "complexity": "advanced"
            }
        ]
        
        return legal_templates

    def generate_chain_of_thoughts(self, question, sparql, template):
        """
        Generate a chain of thoughts explaining how to translate the question to SPARQL
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            template (dict): Template used to generate the question-query pair
        Returns:
            list: List of thought steps
        """
        if "thoughtsTemplate" not in template:
            # Fallback for templates without thoughtsTemplate
            return [
                "1. The question seeks specific information from the Indonesian legal knowledge graph.",
                "2. The query involves entities and relationships defined in the legal domain ontology.",
                "3. Properties in the knowledge graph connect legal documents to their various attributes and relationships.",
                "4. The SPARQL query is constructed to retrieve the requested information efficiently.",
                "5. The result provides valuable insights for legal research and document analysis."
            ]
        
        # Get the thoughts template
        thoughts_template = template["thoughtsTemplate"]
        
        # Extract entity and property URIs from SPARQL
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Create mappings for replacement
        all_mappings = {}
        
        # Add entity mappings
        for i, uri in enumerate(entity_uris):
            key = "entity" if i == 0 else f"entity{i+1}"
            label = legal_entity_label(uri)
            all_mappings[key] = {
                'uri': uri,
                'label': label,
                'prefixed': self.shorten_uri(uri)
            }
        
        # Add value mappings from SPARQL
        numeric_pattern = r'\b(\d+)\b'
        numeric_values = re.findall(numeric_pattern, sparql)
        string_pattern = r'"([^"]+)"'
        string_values = re.findall(string_pattern, sparql)
        
        if numeric_values:
            all_mappings['value'] = {
                'value': numeric_values[0],
                'label': numeric_values[0]
            }
        elif string_values:
            all_mappings['value'] = {
                'value': string_values[0],
                'label': string_values[0]
            }
        
        # Replace placeholders in thoughts
        processed_thoughts = []
        for thought in thoughts_template:
            processed_thought = thought
            
            # Replace each placeholder with the appropriate value
            for placeholder, mapping in all_mappings.items():
                pattern = r'\{' + re.escape(placeholder) + r'\}'
                replacement_value = self.get_appropriate_replacement(thought, placeholder, mapping)
                # print(f"Replacing {pattern} with {replacement_value} in thought: {processed_thought}")
                processed_thought = re.sub(pattern, replacement_value, processed_thought)
            
            # Special handling for first entity: check if {entity} exists, if not try {entity1}
            if 'entity' in all_mappings:
                entity_mapping = all_mappings['entity']
                
                if '{entity}' not in processed_thought and '{entity1}' in processed_thought:
                    pattern = r'\{entity1\}'
                    replacement_value = self.get_appropriate_replacement(thought, 'entity1', entity_mapping)
                    processed_thought = re.sub(pattern, replacement_value, processed_thought)
            
            processed_thoughts.append(processed_thought)
        
        return processed_thoughts

    def get_appropriate_replacement(self, thought_text, placeholder, mapping):
        """
        Determine whether to use URI or label based on the context in the thought
        
        Args:
            thought_text (str): The thought text containing the placeholder
            placeholder (str): The placeholder being replaced
            mapping (dict): The mapping containing uri, label, and prefixed forms
            
        Returns:
            str: The appropriate replacement value
        """
        # Check context around the placeholder to determine appropriate replacement
        thought_lower = thought_text.lower()
        
        # Use URI/prefixed form in these contexts:
        if any(phrase in thought_lower for phrase in [
            "in the ontology",
            "represents the",
            "lex2kg-o:",
            "property '",
            "entity '",
            "via the '",
            "using",
            "through"
        ]):
            # For entity placeholders, use label or entity name without prefix
            if placeholder.startswith('entity') and 'label' in mapping:
                return mapping['label']
            
            # For property placeholders, use prefixed form with lex2kg-o:
            return mapping.get('prefixed', mapping.get('uri', mapping.get('label', placeholder)))
        
        # Use label form in these contexts:
        elif any(phrase in thought_lower for phrase in [
            "categorized as",
            "belonging to", 
            "classified as",
            "of the '",
            "as a '",
            "category '",
            "group '",
            "method '",
            "law '",
            "document '"
        ]):
            return mapping.get('label', mapping.get('value', placeholder))
        
        # Default to label for most contexts
        return mapping.get('label', mapping.get('value', placeholder))
    
    def _extract_uris_from_sparql(self, sparql):
        """
        Extract entity and property URIs from SPARQL query
        
        Args:
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entity_uris, property_uris)
        """
        entity_uris = []
        property_uris = []
        
        # Extract URIs in angle brackets
        uri_pattern = r'<([^>]+)>'
        uris = re.findall(uri_pattern, sparql)
        
        # Extract prefixed names (lex2kg-o:something)
        prefixed_pattern = r'lex2kg-o:([a-zA-Z_][a-zA-Z0-9_]*)'
        prefixed_names = re.findall(prefixed_pattern, sparql)
        
        # Convert prefixed names to full URIs
        lex2kg_prefix = self.prefixes.get('lex2kg-o', 'https://example.org/lex2kg/ontology/')
        for name in prefixed_names:
            full_uri = f"{lex2kg_prefix}{name}"
            uris.append(full_uri)
        
        # Classify URIs as entities or properties
        for uri in uris:
            if self.is_property_uri(uri):
                property_uris.append(uri)
            else:
                entity_uris.append(uri)
        
        return entity_uris, property_uris

    def is_property_uri(self, uri):
        """
        Check if a URI is a property URI
        
        Args:
            uri (str): URI to check
            
        Returns:
            bool: True if it's a property URI
        """
        # Check if it's from the ontology namespace (properties)
        if "ontology/" in uri:
            return True
                
        return False

    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """
        Preprocess question into tokens using NLTK RegexpTokenizer
        
        Args:
            q (str): Question string
            
        Returns:
            list[str]: List of tokens
        """
        tok_pattern = r"\w+"
        tokenizer = RegexpTokenizer(tok_pattern)
        tokenized = tokenizer.tokenize(q)
        result = []
        for tok in tokenized:
            tok = tok.lower()
            if tok not in self.stopwords:
                result.append(tok)
        return result

    def _generate_ngrams(self, tokens: list[str], max_n: int = 3) -> list[str]:
        """
        Generate n-grams from tokens using NLTK
        
        Args:
            tokens (list[str]): List of tokens
            max_n (int): Maximum n-gram size
            
        Returns:
            list[str]: List of n-grams
        """
        result = []
        
        # Generate unigrams, bigrams, and trigrams using NLTK
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            n_grams = ngrams(tokens, n)
            result.extend([" ".join(ng) for ng in n_grams])
        
        return result

    def _search_entities_weaviate(self, query: str, k: int = 5) -> list[dict]:
        """
        Search entities using Weaviate-based approach
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            list[dict]: List of entity results with scores
        """
        if self.property_retrieval:
            try:
                df_result = self.property_retrieval.search_entities(query, k=k)
                results = []
                
                for _, row in df_result.iterrows():
                    results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
                
                return results
            except Exception as e:
                print(f"Error searching entities with Weaviate: {e}")
        
        return []

    def _search_properties_weaviate(self, query: str, k: int = 5) -> list[dict]:
        """
        Search properties using Weaviate-based approach
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            list[dict]: List of property results with scores
        """
        if self.property_retrieval:
            try:
                df_result = self.property_retrieval.search_properties(query, k=k)
                results = []
                
                for _, row in df_result.iterrows():
                    results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
                
                return results
            except Exception as e:
                print(f"Error searching properties with Weaviate: {e}")
        
        return []

    def get_entities_and_properties(self, question, sparql):
        """
        Extract entities and properties from SPARQL query and get their labels using legal_entity_label and legal_property_label
        
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entities_list, properties_list, entity_matches, property_matches)
        """
        # Extract actual URIs from SPARQL query
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Get labels for entities and properties
        entities_list = []
        properties_list = []
        
        # Get entity labels using legal_entity_label function
        for uri in entity_uris:
            label = legal_entity_label(uri)
            if label:
                entities_list.append(label)
        
        # Get property labels using legal_property_label function  
        for uri in property_uris:
            label = legal_property_label(uri)
            if label:
                properties_list.append(label)
        
        # Get entity and property candidates for entities_matches and properties_matches
        property_candidates = entities_list + properties_list
        related_candidates = self.get_related_candidates(
            question, 
            property_candidates=property_candidates,
            threshold=0.6,
            k=5
        )
        
        # Format entity matches
        entity_matches = []
        if "entities" in related_candidates:
            for entity in related_candidates["entities"]:
                expanded_id = self.expand_uri(entity['short'])
                entity_matches.append({
                    "id": expanded_id,
                    "label": entity['label'],
                })
        
        # Format property matches
        property_matches = []
        if "properties" in related_candidates:
            for property in related_candidates["properties"]:
                property_matches.append({
                    "id": property['short'],
                    "label": property['label'],
                })
        
        return entities_list, properties_list, entity_matches, property_matches
    
    def expand_uri(self, shortened_uri):
        """
        Expand a shortened URI back to its full form
        
        Args:
            shortened_uri (str): Shortened URI with prefix (e.g., lex2kg:uu/2010/8)
            
        Returns:
            str: Full URI (e.g., https://example.org/lex2kg/uu/2010/8)
        """
        # Check if the URI has a prefix
        if ":" in shortened_uri:
            prefix, path = shortened_uri.split(":", 1)
            
            # If the prefix is in our known prefixes, expand it
            if prefix in self.prefixes:
                return f"{self.prefixes[prefix]}{path}"
        
        # Return as is if it doesn't have a recognized prefix or is already a full URI
        return shortened_uri

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        threshold: float = 0.6,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """
        Get related entity and property candidates using n-grams and property candidates
        
        Args:
            q (str): Question string
            property_candidates (list[str]): List of property candidates (entities and properties)
            threshold (float): Score threshold for relevance
            k (int): Number of results per search
            
        Returns:
            dict[str, list[str]]: Dictionary with 'entities' and 'properties' lists
        """
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, search_type, threshold=threshold):
            """Search for entities or properties and format results"""

            # Search using the appropriate method
            if search_type == "entities":
                df_res = self._search_entities_weaviate(ngram, k=k)
            else:
                df_res = self._search_properties_weaviate(ngram, k=k)
            
            # Filter by threshold and format results
            filtered_results = []
            for result_item in df_res:
                if result_item['score'] >= threshold:
                    filtered_results.append(result_item)
            
            return search_type, filtered_results

        # Search using n-grams and property candidates
        search_terms = ngrams + property_candidates
        
        for term in search_terms:
            for search_type in result.keys():
                search_result_type, df_res = search(term, search_type)
                if df_res:
                    extracted_items = [{'short': item['short'], 'label': item['label']} for item in df_res]
                    result[search_result_type].extend(extracted_items)
                    
        # Remove duplicates at the end
        for key in result.keys():
            # Convert to list of tuples, use set for deduplication, then back to dicts
            seen = set()
            unique_items = []
            for item in result[key]:
                item_tuple = (item['short'], item['label'])
                if item_tuple not in seen:
                    seen.add(item_tuple)
                    unique_items.append(item)
            result[key] = unique_items
        return result

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
                            # Generate chain of thoughts for the question-query pair
                            thoughts = self.generate_chain_of_thoughts(instance["question"], instance["sparql"], template)
                            
                            # Get entity matches and property matches
                            entities_list, properties_list, entity_matches, property_matches = self.get_entities_and_properties(instance["question"], instance["sparql"])
                            
                            # Success! Add the question-query pair with enhanced fields
                            dataset.append(
                                {
                                    "id": f"q{id_counter}",
                                    "question": instance["question"],
                                    "englishQuestion": instance["englishQuestion"],
                                    "sparql": instance["sparql"],
                                    "category": template["category"],
                                    "complexity": template["complexity"],
                                    "templateId": template["id"],
                                    "thoughts": thoughts,
                                    "entities": entities_list,
                                    "properties": properties_list,
                                    "entities_matches": entity_matches,
                                    "properties_matches": property_matches
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

                                    # Generate thoughts for variation too
                                    var_thoughts = self.generate_chain_of_thoughts(variation["indonesian"], instance["sparql"], template)
                                    var_entities_list, var_properties_list, var_entity_matches, var_property_matches = self.get_entities_and_properties(variation["indonesian"], instance["sparql"])

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
                                            "thoughts": var_thoughts,
                                            "entities": var_entities_list,
                                            "properties": var_properties_list,
                                            "entities_matches": var_entity_matches,
                                            "properties_matches": var_property_matches
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
                        # Extract label using legal_entity_label function
                        entity_label = legal_entity_label(entity_uri)

                    replacement = {
                        "value": self.shorten_uri(entity_uri),
                        "label": entity_label,
                        "uri": entity_uri,
                    }
                elif placeholder == "value" or placeholder.endswith("Value"):
                    # For value placeholders
                    value_str = str(value)

                    # Handle different value types appropriately
                    if "year" in template["id"]:
                        replacement = {"value": value_str, "label": value_str}
                    elif "keyword" in template["id"]:
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"',  # Include quotes for string literal
                        }
                    elif "enactor" in template["id"]:
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
            idx = random.randrange(len(template["questionTemplates"]))
            question_template = template["questionTemplates"][idx]
            english_question_template = template["englishQuestionTemplates"][idx]

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
        idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][idx]
        english_question_template = template["englishQuestionTemplates"][idx]
        
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
        idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][idx]
        english_question_template = template["englishQuestionTemplates"][idx]

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

    def extract_placeholders(self, template):
        """
        Extract all placeholders from template

        Args:
            template (dict): Template with question and SPARQL

        Returns:
            set: Set of placeholder names
        """
        placeholders = set()

        # Check if we have multiple question templates
        question_templates = template["questionTemplates"]
        english_templates = template["englishQuestionTemplates"]

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

            # Use legal_entity_label function to generate label
            entity_label = legal_entity_label(entity_uri)

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
                    "label": legal_entity_label(value_str),
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

        # Write header - updated to include new fields
        writer.writerow([
            'id', 'question', 'englishQuestion', 'sparql', 'category', 
            'complexity', 'templateId', 'thoughts', 'entities', 'properties',
            'entities_matches', 'properties_matches'
        ])

        # Write rows
        for item in dataset:
            sparql_escaped = item["sparql"].replace("\n", " ")
            
            # Convert complex fields to JSON strings for CSV
            thoughts_str = json.dumps(item.get("thoughts", []))
            entities_str = json.dumps(item.get("entities", []))
            properties_str = json.dumps(item.get("properties", []))
            entities_matches_str = json.dumps(item.get("entities_matches", []))
            properties_matches_str = json.dumps(item.get("properties_matches", []))
            
            writer.writerow([
                item["id"],
                item["question"],
                item["englishQuestion"],
                sparql_escaped,
                item["category"],
                item["complexity"],
                item["templateId"],
                thoughts_str,
                entities_str,
                properties_str,
                entities_matches_str,
                properties_matches_str
            ])

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
            