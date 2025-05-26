// frontend/src/utils/api.ts
import { Chat, ChatWithMessages, AgentSettings } from '../types';
import { API_BASE_URL, API_HOST } from '../config/api';

// Helper function to get headers with ngrok support
const getHeaders = (): HeadersInit => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Add ngrok-specific header if using ngrok
  if (API_HOST.includes('ngrok')) {
    headers['ngrok-skip-browser-warning'] = 'true';
  }

  return headers;
};

export const fetchChats = async (): Promise<Chat[]> => {
  const response = await fetch(`${API_BASE_URL}/chats/`, {
    method: 'GET',
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch chats: ${response.status} ${response.statusText}`);
  }
  return response.json();
};

export const fetchChat = async (chatId: string): Promise<ChatWithMessages> => {
  const response = await fetch(`${API_BASE_URL}/chats/${chatId}/`, {
    method: 'GET',
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch chat: ${response.status} ${response.statusText}`);
  }
  return response.json();
};

export const createChat = async (): Promise<Chat> => {
  const response = await fetch(`${API_BASE_URL}/chats/`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to create chat: ${response.status} ${response.statusText}`);
  }
  return response.json();
};

export const deleteChat = async (chatId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/chats/${chatId}/`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to delete chat: ${response.status} ${response.statusText}`);
  }
};

export const sendMessage = async (chatId: string, message: string, settings: AgentSettings): Promise<{ status: string }> => {
  const response = await fetch(`${API_BASE_URL}/chats/${chatId}/send_message/`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({
      message,
      settings
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
  }
  return response.json();
};
