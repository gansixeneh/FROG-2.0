// frontend/src/context/ChatContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Chat, ChatWithMessages, Message, DebugOutput } from '../types';
import { fetchChats, fetchChat, createChat } from '../utils/api';

interface ChatContextType {
  chats: Chat[];
  currentChat: ChatWithMessages | null;
  debugOutput: DebugOutput[];
  isNavOpen: boolean;
  isLoading: boolean;
  socket: WebSocket | null;
  loadChat: (chatId: string) => Promise<void>;
  startNewChat: () => Promise<void>;
  sendMessage: (content: string) => void;
  toggleNav: () => void;
  clearDebugOutput: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChat, setCurrentChat] = useState<ChatWithMessages | null>(null);
  const [debugOutput, setDebugOutput] = useState<DebugOutput[]>([]);
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [socket, setSocket] = useState<WebSocket | null>(null);

  // Fetch all chats on initial load
  useEffect(() => {
    const loadChats = async () => {
      try {
        const chatList = await fetchChats();
        setChats(chatList);
        
        // If there are no chats, automatically create a new one
        if (chatList.length === 0) {
          await startNewChat();
        } else if (!currentChat) {
          // If there are chats but none is selected, load the most recent one
          await loadChat(chatList[0].id);
        }
        
        setIsLoading(false);
      } catch (error) {
        console.error('Error loading chats:', error);
        setIsLoading(false);
      }
    };
    
    loadChats();
  }, []);

  // Load a specific chat
  const loadChat = async (chatId: string) => {
    try {
      setIsLoading(true);
      const chatData = await fetchChat(chatId);
      setCurrentChat(chatData);
      
      // Close existing socket if open
      if (socket) {
        socket.close();
      }
      
      // Connect to WebSocket for this chat
      const wsUrl = `ws://localhost:8000/ws/chat/${chatId}/`;

      console.log('Connecting to WebSocket:', wsUrl);
      
      const newSocket = new WebSocket(wsUrl);
      setSocket(newSocket);
      
      // Clear debug output for new chat
      setDebugOutput([]);
      
      // Set up WebSocket event handlers
      newSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.debug) {
          // Handle debug output
          setDebugOutput(prev => [...prev, {
            content: data.debug,
            timestamp: new Date().toISOString()
          }]);
        } else if (data.role && data.message) {
          // Handle new message
          const newMessage: Message = {
            id: `temp-${Date.now()}`,  // Temporary ID until we refresh
            role: data.role,
            content: data.message,
            created_at: new Date().toISOString()
          };
          
          setCurrentChat(prev => {
            if (!prev) return null;
            return {
              ...prev,
              messages: [...prev.messages, newMessage]
            };
          });
          
          // If it's a system message indicating completion, refresh the chat data
          if (data.role === 'assistant') {
            refreshCurrentChat();
          }
        }
      };
      
      newSocket.onopen = () => {
        console.log('WebSocket connection established');
      };
      
      newSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
      newSocket.onclose = () => {
        console.log('WebSocket connection closed');
      };
      
      // Close sidebar on mobile after selecting a chat
      setIsNavOpen(false);
      setIsLoading(false);
    } catch (error) {
      console.error('Error loading chat:', error);
      setIsLoading(false);
    }
  };

  // Refresh current chat data from API
  const refreshCurrentChat = async () => {
    if (currentChat) {
      try {
        const refreshedChat = await fetchChat(currentChat.id);
        setCurrentChat(refreshedChat);
        
        // Also refresh the chats list
        const chatList = await fetchChats();
        setChats(chatList);
      } catch (error) {
        console.error('Error refreshing chat:', error);
      }
    }
  };

  // Start a new chat
  const startNewChat = async () => {
    try {
      setIsLoading(true);
      const newChat = await createChat();
      
      // Add new chat to list
      setChats(prev => [newChat, ...prev]);
      
      // Load the new chat
      await loadChat(newChat.id);
      
      setIsNavOpen(false);
      setIsLoading(false);
    } catch (error) {
      console.error('Error creating new chat:', error);
      setIsLoading(false);
    }
  };

  // Send a message
  const sendMessage = (content: string) => {
    if (!socket || socket.readyState !== WebSocket.OPEN || !currentChat) {
      console.error('WebSocket is not connected');
      return;
    }
    
    // Add user message to UI immediately
    const newMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString()
    };
    
    setCurrentChat(prev => {
      if (!prev) return null;
      return {
        ...prev,
        messages: [...prev.messages, newMessage]
      };
    });
    
    // Send message to WebSocket
    socket.send(JSON.stringify({
      message: content
    }));
  };

  // Toggle side navigation
  const toggleNav = () => {
    setIsNavOpen(prev => !prev);
  };

  // Clear debug output
  const clearDebugOutput = () => {
    setDebugOutput([]);
  };

  return (
    <ChatContext.Provider value={{
      chats,
      currentChat,
      debugOutput,
      isNavOpen,
      isLoading,
      socket,
      loadChat,
      startNewChat,
      sendMessage,
      toggleNav,
      clearDebugOutput
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};