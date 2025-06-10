// frontend/src/config/api.ts
// Configuration for API and Pusher connections

// Default host is the ngrok URL
const DEFAULT_HOST = "prepared-sheep-similarly.ngrok-free.app";

// Check if the environment has a custom API host
export const API_HOST = process.env.REACT_APP_API_HOST || DEFAULT_HOST;

// Determine API protocol (use HTTPS for production/ngrok, HTTP for localhost)
export const API_PROTOCOL = API_HOST.includes("localhost") ? "http" : "https";

// Build the base URLs
export const API_BASE_URL = `${API_PROTOCOL}://${API_HOST}/api`;

// Pusher configuration
export const PUSHER_CONFIG = {
  key: "0379edb726d89ea8c1e9",
  cluster: "ap1",
  forceTLS: true,
};

// Helper function to get chat channel name
export const getChatChannelName = (chatId: string): string => {
  return `chat_${chatId}`;
};
