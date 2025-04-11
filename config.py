# config.py
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# API Keys and Endpoints
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# Tool Configuration
MAX_ENTITY_CANDIDATES = 5
MAX_PROPERTY_CANDIDATES = 10
MAX_QUERY_ATTEMPTS = 3
SIMILARITY_THRESHOLD = 0.7

# Model Configuration
SENTENCE_TRANSFORMER_MODEL = "multi-qa-mpnet-base-cos-v1"