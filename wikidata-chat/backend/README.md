# Wikidata Agent Backend

This is the Django backend for the Wikidata Agent chat application.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key

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
4. Create a `.env` file in the project root with your Google Gemini API key:

   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ALWAYS_USE_GENERATE_SPARQL=false
   ```
   
   Configuration options:
   - `GEMINI_API_KEY`: Required. Your Google Gemini API key.
   - `ALWAYS_USE_GENERATE_SPARQL`: Optional (default: false). When set to "true", the agent will always use SPARQL generation for all queries, bypassing the verbalization approach.

5. Run database migrations:

   ```

   python manage.py makemigrations chat

   python manage.py migrate

   ```
6. Start the development server:

   ```

   python manage.py runserver

   ```

The server should now be running at http://localhost:8000.

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
