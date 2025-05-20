// frontend/src/utils/api.ts
import { Chat, ChatWithMessages } from '../types';
import { API_BASE_URL } from '../config/api';

export const fetchChats = async (): Promise<Chat[]> => {
  const response = await fetch(`${API_BASE_URL}/chats/`);
  if (!response.ok) {
    throw new Error('Failed to fetch chats');
  }
  return response.json();
};

export const fetchChat = async (chatId: string): Promise<ChatWithMessages> => {
  const response = await fetch(`${API_BASE_URL}/chats/${chatId}/`);
  if (!response.ok) {
    throw new Error('Failed to fetch chat');
  }
  return response.json();
};

export const createChat = async (): Promise<Chat> => {
  const response = await fetch(`${API_BASE_URL}/chats/`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to create chat');
  }
  return response.json();
};

export const deleteChat = async (chatId: string): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/chats/${chatId}/`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete chat');
  }
};