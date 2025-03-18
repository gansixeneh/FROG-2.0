from dotenv import load_dotenv
import os

load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

os.environ["WEAVIATE_URL"] = WEAVIATE_URL
os.environ["WEAVIATE_API_KEY"] = WEAVIATE_API_KEY
os.environ["WEAVIATE_URL"] = HF_TOKEN
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
