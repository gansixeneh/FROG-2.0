# Frontend Configuration Guide

## Connection Settings

By default, the frontend connects to:
- **Default API URL**: `https://boss-amoeba-flying.ngrok-free.app/api`
- **Default WebSocket URL**: `wss://boss-amoeba-flying.ngrok-free.app/ws`

These settings ensure the application works with the deployed backend by default.

## Connecting to Local Development Server

To connect to a local development server instead of the default ngrok URL:

### Option 1: Using .env.local (Recommended)

Create a `.env.local` file in the frontend directory with:

```
REACT_APP_API_HOST=localhost:8000
```

This will automatically use:
- `http://localhost:8000/api` for REST API calls
- `ws://localhost:8000/ws` for WebSocket connections

### Option 2: Using .env.development

For development mode only, you can use the included `.env.development` file which already contains the local settings. This file is applied automatically in development mode.

### Option 3: Environment Variables at Runtime

Set the environment variable when starting the application:

```bash
# For Linux/macOS
REACT_APP_API_HOST=localhost:8000 npm start

# For Windows PowerShell
$env:REACT_APP_API_HOST="localhost:8000"; npm start
```

## Troubleshooting Connection Issues

If you encounter connection issues, check:

1. That your backend server is running and accessible at the configured URL
2. That WebSocket connections are properly supported by your network environment
3. The browser console for any connection error messages

## Frog Reasoning UI

The Frog Reasoning UI displays system messages that show the agent's reasoning process. If this UI is not displaying correctly:

1. Check that debug messages are being properly received from the backend
2. Make sure the WebSocket connection is established successfully
3. Verify that the backend is correctly sending debug info through the WebSocket
