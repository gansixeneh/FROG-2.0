# Wikidata Agent Chat Application

A full-stack web application that integrates a Wikidata Agent with a modern React frontend and Django backend. This application allows users to ask questions and get answers from Wikidata through a chat interface with real-time updates via WebSockets.

## Features

- Modern chat interface similar to Claude's web interface
- Real-time updates of the agent's reasoning process
- Chat history management with a side menu
- Detailed traceability of the agent's reasoning process
- WebSocket connection for real-time communication

## Project Structure

The project is structured as follows:

```
wikidata-chat/
├── backend/              # Django backend
│   ├── agent/            # Modified Wikidata Agent
│   ├── chat/             # Chat application
│   ├── tools/            # Wikidata tools (from original project)
│   ├── wikidata_web/     # Django project settings
│   ├── .env              # Environment file for API keys
│   ├── manage.py         # Django management script
│   └── requirements.txt  # Python dependencies
└── frontend/             # React frontend
    ├── public/           # Static assets
    ├── src/              # Source code
    │   ├── components/   # React components
    │   ├── context/      # Context providers
    │   ├── types/        # TypeScript interfaces
    │   └── utils/        # Utility functions
    ├── package.json      # Node.js dependencies
    └── tailwind.config.js # Tailwind CSS configuration
```

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Google Gemini API key

## Installation and Setup

### 1. Clone the Repository

First, clone the repository and navigate to the project directory:

```bash
git clone https://github.com/yourusername/wikidata-chat.git
cd wikidata-chat
```

### 2. Backend Setup

Navigate to the backend directory and set up the Python environment:

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the backend directory and add your Google Gemini API key:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Run the migrations to set up the database:

```bash
python manage.py makemigrations chat
python manage.py migrate
```

### 3. Frontend Setup

In a new terminal, navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
```

#### Environment Configuration

By default, the frontend connects to the ngrok URL `boss-amoeba-flying.ngrok-free.app`. 

If you want to use a local backend instead:

1. Create an `.env.local` file in the frontend directory:
```
REACT_APP_API_HOST=localhost:8000
```

2. Restart the development server if it's already running.

### 4. Start the Application

#### Start the Backend

In the backend directory with the virtual environment activated:

```bash
python manage.py runserver
```

The Django server will start at http://localhost:8000.

#### Start the Frontend

In the frontend directory:

```bash
npm start
```

The React development server will start at http://localhost:3000.

## Usage

1. Open your browser and navigate to http://localhost:3000
2. Click on "New Chat" to start a new conversation
3. Type your question in the input field and press Enter
4. View the agent's response and real-time tracing of its reasoning process
5. Access previous chats from the side menu

## Example Questions

Try asking the agent questions like:

1. "Who is the current president of France?"
2. "What is the capital of Japan and what is its population?"
3. "List the spouses of Albert Einstein"
4. "Which mountains in the Himalayas are higher than 8000 meters?"
5. "What books did Isaac Asimov write?"

## How it Works

1. The frontend sends the user's question to the backend via WebSocket
2. The backend processes the question using the Wikidata Agent:
   - It searches for entities and properties in Wikidata
   - It constructs and executes SPARQL queries
   - It sends real-time updates back to the frontend
3. The frontend displays the results and the agent's reasoning process

## Customization

### Backend

- Modify the agent's behavior by editing `backend/agent/agent.py`
- Add new tools by extending the tools in the `backend/tools/` directory
- Change API endpoints by editing `backend/chat/views.py`

### Frontend

- Change the UI styling by modifying the components in `frontend/src/components/`
- Update the application behavior by editing the context in `frontend/src/context/ChatContext.tsx`
- Modify the theme by editing `frontend/tailwind.config.js`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
