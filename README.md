# FrOG: Framework of Open GraphRAG

FrOG (Framework of Open GraphRAG) is a full-stack web application that enables natural language querying of knowledge graphs. It integrates a sophisticated GraphRAG agent with a modern React frontend and Django backend, allowing users to ask questions and receive answers through an intuitive chat interface with real-time reasoning visualization.

![FrOG Logo](frontend/public/assets/frog-logo.svg)

## Features

- **Modern Chat Interface**: Clean, responsive design similar to Claude's web interface
- **Real-time Reasoning Visualization**: Watch the agent's thinking process as it answers your questions
- **Multiple Knowledge Sources**: Switch between different knowledge graphs:
  - **Wikidata**: Comprehensive public knowledge graph with millions of entities
  - **Curriculum KB**: University curriculum knowledge base
  - **Legal Document KB**: Indonesian legal document knowledge base
  - **GESIS Scholarly KB**: GESIS scholarly articles knowledge base
- **Runtime Settings Control**:
  - **Use Verbalization**: Toggle between entity verbalization and SPARQL generation approaches
  - **Google Search Fallback**: Enable/disable Google Search when knowledge graph methods fail
  - **Translation Support**: Automatic detection and translation of non-English questions
- **Chat History Management**: Save, browse, and reload previous conversations
- **Detailed Traceability**: Download visualization files (JSON, Mermaid diagrams, TTL graphs)
- **Apache Jena Integration**: Semantic querying of agent execution patterns
- **Multi-provider LLM Support**: Use Google Gemini or local Ollama models

## Architecture

The project uses a modular architecture:

1. **Frontend**: React application with Tailwind CSS for styling
2. **Backend**: Django with LangGraph-based agent architecture
3. **Knowledge Graphs**: Accessible via SPARQL endpoints
4. **LLM Integration**: Configurable multi-provider system
5. **Real-time Communication**: WebSockets for streaming agent reasoning
6. **Visualization**: Apache Jena Fuseki for execution logging and analysis

## Project Structure

```
wikidata-chat/
├── backend/              # Django backend
│   ├── agent/            # Modified Wikidata Agent
│   ├── chat/             # Chat application
│   ├── tools/            # Wikidata tools
│   ├── wikidata_web/     # Django project settings
│   ├── .env              # Environment file for API keys
│   ├── manage.py         # Django management script
│   └── requirements.txt  # Python dependencies
├── frontend/             # React frontend
│   ├── public/           # Static assets
│   ├── src/              # Source code
│   │   ├── components/   # React components
│   │   ├── context/      # Context providers
│   │   ├── types/        # TypeScript interfaces
│   │   └── utils/        # Utility functions
│   ├── package.json      # Node.js dependencies
│   └── tailwind.config.js # Tailwind CSS configuration
└── fuseki-data/          # Apache Jena Fuseki configuration
    ├── config.ttl        # Fuseki configuration file
    ├── create_config.sh  # Script to generate configuration
    └── start_apache_jena.sh # Script to start Fuseki server
```

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Google Gemini API key (required)
- Apache Jena Fuseki server (required for visualization logs)
- Weaviate server (required for vector search)
- Ollama installation (optional, only for running local models)

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

Create a `.env` file in the backend directory and add your API keys:

```
GEMINI_API_KEY=your_gemini_api_key_here
APACHE_JENA_URL=http://localhost:3030
WEAVIATE_URL=localhost
WEAVIATE_HTTP_PORT=8080
WEAVIATE_GRPC_PORT=50052
```

Run the migrations to set up the database:

```bash
python manage.py makemigrations chat
python manage.py migrate
```

### 3. Apache Jena Fuseki Setup

Navigate to the fuseki-data directory and set up the Fuseki server:

```bash
cd ../fuseki-data

# Make the scripts executable
chmod +x start_apache_jena.sh create_config.sh

# Start the Fuseki server
./start_apache_jena.sh
```

The Fuseki server will start at http://localhost:3030.

### 4. Weaviate Setup

Use the included docker-compose file in the `weaviate` directory:

```bash
cd ../backend/weaviate
docker-compose up -d
```

### 5. Frontend Setup

In a new terminal, navigate to the frontend directory and install dependencies:

```bash
cd ../../frontend
npm install
```

#### Environment Configuration

By default, the frontend connects to the ngrok URL `prepared-sheep-similarly.ngrok-free.app`.

If you want to use a local backend instead:

1. Create an `.env.local` file in the frontend directory:

```
REACT_APP_API_HOST=localhost:8000
```

2. Restart the development server if it's already running.

### 6. Start the Application

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
3. **Configure Settings**: Click the "Settings" button in the header to configure:
   - **Use Verbalization**: When enabled, FrOG tries entity verbalization first for simple questions
   - **Google Search Fallback**: When enabled, uses Google Search if knowledge graph methods fail
   - **Translation**: When enabled, automatically detects and translates non-English questions
   - **Knowledge Source**: Switch between Wikidata, Curriculum, Legal, and GESIS sources
4. Type your question in the input field and press Enter
5. View the agent's response and real-time tracing of its reasoning process
6. Access previous chats from the side menu
7. Download visualization files for further analysis

## Example Questions

Try asking the agent questions like:

1. "Who is the current president of France?"
2. "What is the capital of Japan and what is its population?"
3. "List the spouses of Albert Einstein"
4. "Which mountains in the Himalayas are higher than 8000 meters?"
5. "What books did Isaac Asimov write?"

## LLM Configuration System

The backend supports multiple LLM providers through a configuration-based system:

### Supported Providers

1. **Gemini** - Google's Gemini models via API
2. **Ollama** - Local models via Ollama (optional)

### Configuration

The LLM configuration is stored in `config/llm_config.json`. You can customize which models are used for different tasks:

- **EntityExtractionNode**: For extracting entities and properties from questions
- **VerbalizationNode**: For generating natural language descriptions from knowledge graph data
- **SparqlGenerationNode**: For generating SPARQL queries
- **AnswerGenerationNode**: For generating final answers to user questions

An example configuration file is provided in `config/llm_config.example.json`.

## Agent Architecture

The backend uses a LangGraph-based agent architecture with the following components:

- **TranslationNode**: Translates non-English questions
- **EntityExtractionNode**: Extracts entities and properties from questions
- **StrategySelectionNode**: Decides between verbalization and SPARQL approaches
- **VerbalizationNode**: Retrieves entity information directly
- **PropertyGenerationNode**: Enhances properties for SPARQL queries
- **SparqlGenerationNode**: Generates and executes SPARQL queries
- **AnswerGenerationNode**: Generates final natural language answers
- **GoogleSearchNode**: Fallback option when knowledge graph queries fail

## Apache Jena Visualization Analysis

This project integrates with Apache Jena Fuseki to store visualization logs in RDF format. This enables powerful semantic querying of agent execution patterns. You can access the Jena logs interface by clicking the "Logs" button in the header.

The following query types are available:
- List all runs with timestamps
- Find runs with specific entities
- Find SPARQL queries used in runs
- Analyze approach distribution
- Calculate average duration by component
- Find most common entities and properties
- Track failed vs successful SPARQL queries
- Analyze query performance over time

## Customization

### Backend

- Modify the agent's behavior by editing `backend/agent/agent.py`
- Add new tools by extending the tools in the `backend/tools/` directory
- Change API endpoints by editing `backend/chat/views.py`
- Configure LLM providers in `config/llm_config.json`

### Frontend

- Change the UI styling by modifying the components in `frontend/src/components/`
- Update the application behavior by editing the context in `frontend/src/context/ChatContext.tsx`
- Modify the theme by editing `frontend/tailwind.config.js`

## License

This project is licensed under the MIT License.