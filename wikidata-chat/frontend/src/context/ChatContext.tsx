// frontend/src/context/ChatContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Chat, ChatWithMessages, Message } from '../types';
import { fetchChats, fetchChat, createChat } from '../utils/api';

interface ChatContextType {
  chats: Chat[];
  currentChat: ChatWithMessages | null;
  isNavOpen: boolean;
  isLoading: boolean;
  isProcessing: boolean; // New state to track if a message is being processed
  socket: WebSocket | null;
  loadChat: (chatId: string) => Promise<void>;
  startNewChat: () => Promise<void>;
  sendMessage: (content: string) => void;
  toggleNav: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Set of already processed message IDs to prevent duplicates
const processedMessageIds = new Set<string>();

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChat, setCurrentChat] = useState<ChatWithMessages | null>(null);
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false); // New state for message processing
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [socketConnected, setSocketConnected] = useState(false);

  // Clear processed message IDs when switching chats
  const clearProcessedMessageIds = () => {
    processedMessageIds.clear();
  };

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

  // Create a separate effect for WebSocket connection
  useEffect(() => {
    // Clean up function to close the socket when component unmounts
    // or when currentChat changes
    return () => {
      if (socket) {
        console.log('Closing WebSocket connection due to effect cleanup');
        socket.close();
        setSocketConnected(false);
      }
    };
  }, [currentChat?.id]);

  // Setup WebSocket connection
  const setupWebSocket = (chatId: string) => {
    // Close existing socket if open
    if (socket) {
      console.log('Closing existing WebSocket connection');
      socket.close();
      setSocketConnected(false);
    }

    // Clear the set of processed message IDs when setting up a new WebSocket
    clearProcessedMessageIds();

    // Create new WebSocket connection
    const wsUrl = `ws://localhost:8000/ws/chat/${chatId}/`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    const newSocket = new WebSocket(wsUrl);
    setSocket(newSocket);
    
    // Set up WebSocket event handlers
    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const messageId = data.message_id || `fallback-${Date.now()}-${Math.random()}`;
      
      // Skip if we've already processed this message
      if (processedMessageIds.has(messageId)) {
        console.log(`Skipping duplicate message with ID: ${messageId}`);
        return;
      }
      
      // Add to processed message set
      processedMessageIds.add(messageId);
      
      if (data.role && (data.message || data.debug)) {
        // Handle new message
        const newMessage: Message = {
          id: messageId,
          role: data.role,
          content: data.message || data.debug,
          created_at: new Date().toISOString()
        };
        
        setCurrentChat(prev => {
          if (!prev) return null;
          
          return {
            ...prev,
            messages: [...prev.messages, newMessage]
          };
        });
        
        if (data.role === 'assistant') {
          setIsProcessing(false);
          refreshChatsList();
        }
      }
    };
    
    newSocket.onopen = () => {
      console.log('WebSocket connection established');
      setSocketConnected(true);
    };
    
    newSocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setSocketConnected(false);
      setIsProcessing(false); // Reset processing state on error
    };
    
    newSocket.onclose = (event) => {
      console.log('WebSocket connection closed', event.code, event.reason);
      setSocketConnected(false);
      setIsProcessing(false); // Reset processing state on close
      
      // If the socket closed unexpectedly (not by our code), attempt to reconnect
      if (event.code !== 1000 && currentChat?.id === chatId) {
        console.log('Attempting to reconnect WebSocket...');
        setTimeout(() => setupWebSocket(chatId), 2000);
      }
    };

    return newSocket;
  };

  // Load a specific chat
  const loadChat = async (chatId: string) => {
    try {
      setIsLoading(true);
      const chatData = await fetchChat(chatId);
      setCurrentChat(chatData);
      
      // Clear processed message IDs when loading a new chat
      clearProcessedMessageIds();
      
      // Add existing message IDs to the processed set
      chatData.messages.forEach(msg => {
        processedMessageIds.add(msg.id);
      });
      
      // Connect to WebSocket for this chat
      setupWebSocket(chatId);
      
      // Close sidebar on mobile after selecting a chat
      setIsNavOpen(false);
      setIsLoading(false);
    } catch (error) {
      console.error('Error loading chat:', error);
      setIsLoading(false);
    }
  };

  // Refresh just the chats list without affecting the websocket
  const refreshChatsList = async () => {
    try {
      const chatList = await fetchChats();
      setChats(chatList);
    } catch (error) {
      console.error('Error refreshing chats list:', error);
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
    // Don't allow sending if already processing a message
    if (isProcessing) {
      console.log('Message already being processed, ignoring new message');
      return;
    }

    if (!socket || socket.readyState !== WebSocket.OPEN || !currentChat) {
      console.error('WebSocket is not connected, attempting to reconnect...');
      // Try to reconnect if socket is not open
      if (currentChat) {
        const newSocket = setupWebSocket(currentChat.id);
        
        // Wait a short time for the connection to establish, then send the message
        setTimeout(() => {
          if (newSocket.readyState === WebSocket.OPEN) {
            sendMessageToSocket(newSocket, content, currentChat);
          } else {
            // Give it one more chance after a longer delay
            setTimeout(() => {
              if (newSocket.readyState === WebSocket.OPEN) {
                sendMessageToSocket(newSocket, content, currentChat);
              } else {
                console.error('Failed to reconnect WebSocket');
                alert('Connection error. Please refresh the page and try again.');
                setIsProcessing(false); // Reset processing state on error
              }
            }, 1000);
          }
        }, 300);
      }
      return;
    }
    
    // Socket is open, send message directly
    sendMessageToSocket(socket, content, currentChat);
  };

  // Helper to send message to a socket
  const sendMessageToSocket = (
    socketToUse: WebSocket, 
    content: string, 
    chat: ChatWithMessages
  ) => {
    // Set processing state to true
    setIsProcessing(true);
    
    // Create a temporary message ID
    const tempId = `temp-${Date.now()}`;
    
    // Add to processed set to prevent duplication when real message comes back
    processedMessageIds.add(tempId);
    
    // Add user message to UI immediately
    const newMessage: Message = {
      id: tempId,
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
    socketToUse.send(JSON.stringify({
      message: content
    }));
  };

  // Toggle side navigation
  const toggleNav = () => {
    setIsNavOpen(prev => !prev);
  };

  return (
    <ChatContext.Provider value={{
      chats,
      currentChat,
      isNavOpen,
      isLoading,
      isProcessing,
      socket,
      loadChat,
      startNewChat,
      sendMessage,
      toggleNav
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