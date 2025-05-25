# Wikidata Agent Backend

This is the Django backend for the Wikidata Agent chat application with multi-provider LLM support.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key (required)
- Optional: Kaggle API credentials (for Kaggle models)
- Optional: Unsloth installation (for local fine-tuned models)

### Setup

1. Create a virtual environment:

   ```
   python -m venv venv
   ```

2. Activate the virtual environment:

- On Windows:

  ```
  venv\Scripts\activate
  ```
- On macOS/Linux:

  ```
  source venv/bin/activate
  ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. **Optional dependencies** (install based on which LLM providers you want to use):

   ```bash
   # For Unsloth provider (local fine-tuned models)
   pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
   
   # For Kaggle provider (already included in requirements.txt)
   pip install kaggle
   ```

5. Create a `.env` file in the project root with your API keys:

   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ALWAYS_USE_GENERATE_SPARQL=false
   
   # Optional: For Kaggle provider
   KAGGLE_USERNAME=your_kaggle_username
   KAGGLE_KEY=your_kaggle_api_key
   ```
   
   **Configuration options:**
   - `GEMINI_API_KEY`: **Required**. Your Google Gemini API key.
   - `ALWAYS_USE_GENERATE_SPARQL`: Optional (default: false). When set to "true", the agent will always use SPARQL generation for all queries, bypassing the verbalization approach.
   - `KAGGLE_USERNAME` & `KAGGLE_KEY`: Optional. Required only if using Kaggle models for SPARQL generation.

6. Run database migrations:

   ```
   python manage.py makemigrations chat
   python manage.py migrate
   ```

7. Start the development server:

   ```
   python manage.py runserver
   ```

The server should now be running at http://localhost:8000.

## LLM Configuration System

The backend now supports multiple LLM providers through a configuration-based system:

### Supported Providers

1. **Gemini** - Google's Gemini models via API
2. **Unsloth** - Local fine-tuned models using Unsloth's FastLanguageModel
3. **Kaggle** - Models downloaded from Kaggle and loaded with Unsloth

### Configuration

The LLM configuration is stored in `config/llm_config.json`. You can customize which models are used for different tasks:

- **EntityExtractionNode**: Currently configured to use Unsloth with Qwen2.5-3B-Instruct-bnb-4bit
- **VerbalizationNode**: Uses Gemini 2.0 Flash
- **SparqlGenerationNode**: Configured to use a fine-tuned Kaggle model
- **AnswerGenerationNode**: Uses Gemini 1.5 Pro

### Testing the Configuration

Test your LLM factory setup:

```bash
python test_llm_factory.py
```

See example usage:

```bash
python example_llm_factory_usage.py
```

### Provider-Specific Setup

#### Unsloth Provider
- Requires Unsloth installation (see optional dependencies above)
- Loads models locally using `FastLanguageModel.from_pretrained()`
- Supports chat templates automatically
- Uses GPU memory - ensure adequate VRAM

#### Kaggle Provider  
- Requires Kaggle API credentials in environment variables
- Downloads datasets automatically to `./kaggle_models/` directory
- Caches downloaded models to avoid re-downloading
- Uses Unsloth for model loading after download

#### Gemini Provider
- Uses Google's generative AI API
- Requires only the `GEMINI_API_KEY` environment variable
- No local storage requirements

## API Endpoints

-`GET /api/chats/` - List all chats

-`POST /api/chats/` - Create a new chat

-`GET /api/chats/<uuid>/` - Get a chat with all messages

-`DELETE /api/chats/<uuid>/` - Delete a chat

## WebSocket Connection

To connect to a chat via WebSocket, use the following URL:

```

ws://localhost:8000/ws/chat/<chat_uuid>/

```

You can send messages to the WebSocket in the following format:

```json

{

"message": "Your question here"

}

```

The WebSocket will send back messages in the following formats:

- Regular messages:

```json

{

"message": "Message content",

"role": "user|assistant|system"

}

```


- Debug messages:

```json

{

"debug": "Debug output content",

"role": "system"

}

```
