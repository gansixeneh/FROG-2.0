# FrOG Frontend

This directory contains the React frontend application for FrOG (Framework of Open GraphRAG), a system that enables natural language querying of knowledge graphs.

## Overview

The FrOG frontend provides a chat interface for interacting with the GraphRAG system. It allows users to ask questions in natural language and receive answers based on knowledge graphs. The system searches for entities, constructs SPARQL queries, and provides detailed explanations of its reasoning process.

## Features

-**Chat Interface**: Clean and responsive interface for conversing with the FrOG agent

-**Multiple Knowledge Sources**: Switch between Wikidata, Curriculum, Legal, and GESIS scholarly knowledge graphs

-**Reasoning Transparency**: View the agent's reasoning process, including entity recognition, query construction, and execution

-**Visualization Files**: Download JSON, Mermaid diagrams, and TTL graphs for further analysis

-**Real-time Updates**: See the agent's thinking process in real-time via Pusher integration

-**Translation Support**: Automatic detection and translation of non-English questions

-**Google Search Fallback**: Option to use Google Search when knowledge graph methods are insufficient

-**Settings Management**: Configure agent behavior through a user-friendly settings panel

-**Execution Logs**: Access and analyze visualization logs through Apache Jena Fuseki

## Tech Stack

- React 18
- TypeScript
- Tailwind CSS
- Pusher.js for real-time communication
- React Markdown for rendering markdown content
- SPARQL Formatter for formatting SPARQL queries

## Setup Instructions

1. Clone the repository
2. Navigate to the `frontend` directory
3. Install dependencies:

   ```bash

   ```

npm install

````

4. Create a `.env.local` file based on `.env.example` (if needed to customize the API host)

5. Start the development server:

   ```bash

npm start

````

The application will be available at [http://localhost:3000](http://localhost:3000).

## Environment Configuration

The application connects to the backend API using the following environment variables:

-`REACT_APP_API_HOST`: The hostname of the API server (defaults to `prepared-sheep-similarly.ngrok-free.app` if not specified)

You can override this in `.env.local` for local development:

```

REACT_APP_API_HOST=localhost:8000

```

## Project Structure

-`src/components`: UI components including chat interface, message display, etc.

-`src/context`: React context for global state management

-`src/services`: Service classes for external integrations (e.g., Pusher)

-`src/utils`: Utility functions for API calls, SPARQL formatting, etc.

-`src/types`: TypeScript interfaces and type definitions

-`src/config`: Configuration constants

-`src/styles`: Custom CSS styles

## Key Components

-`ChatArea.tsx`: Main chat display area

-`ChatMessage.tsx`: Individual message rendering

-`MessageInput.tsx`: Input field for sending messages

-`Header.tsx`: Top navigation bar

-`SideNav.tsx`: Chat history sidebar

-`Settings.tsx`: Settings configuration panel

-`JenaLogsModal.tsx`: Interface for accessing Apache Jena logs

-`SystemMessageGroup.tsx`: Displays agent reasoning traces

## API Integration

The frontend communicates with the backend using a RESTful API. Key endpoints include:

- GET `/api/chats/`: Retrieve all chats
- GET `/api/chats/{id}/`: Get a specific chat with messages
- POST `/api/chats/`: Create a new chat
- POST `/api/chats/{id}/send_message/`: Send a message in a specific chat

Real-time updates are received through Pusher channels for each chat.

## Styling

The application uses Tailwind CSS for styling with a custom frog-themed color palette defined in `tailwind.config.js`.
