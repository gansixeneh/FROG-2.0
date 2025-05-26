// frontend/src/config/api.ts
// Configuration for API and WebSocket connections

// Default host is the ngrok URL
const DEFAULT_HOST = 'boss-amoeba-flying.ngrok-free.app';

// Check if the environment has a custom API host
export const API_HOST = process.env.REACT_APP_API_HOST || DEFAULT_HOST;
console.log('Using API host: %s', API_HOST);

// Determine API protocol (use HTTPS for production/ngrok, HTTP for localhost)
export const API_PROTOCOL = API_HOST.includes('localhost') ? 'http' : 'https';

// Determine WebSocket protocol (use WSS for production/ngrok, WS for localhost)
export const WS_PROTOCOL = API_HOST.includes('localhost') ? 'ws' : 'wss';

// Build the base URLs
export const API_BASE_URL = `${API_PROTOCOL}://${API_HOST}/api`;
export const WS_BASE_URL = `${WS_PROTOCOL}://${API_HOST}/ws`;

// WebSocket URL builder function
export const getWebSocketUrl = (chatId: string): string => {
  return `${WS_BASE_URL}/chat/${chatId}/`;
};
