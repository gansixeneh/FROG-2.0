// frontend/src/context/ChatContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Chat, ChatWithMessages, Message, DebugOutput, MessageTracing } from '../types';
import { fetchChats, fetchChat, createChat } from '../utils/api';

interface ChatContextType {
  chats: Chat[];
  currentChat: ChatWithMessages | null;
  isNavOpen: boolean;
  isLoading: boolean;
  isProcessing: boolean;
  socket: WebSocket | null;
  loadChat: (chatId: string) => Promise<void>;
  startNewChat: () => Promise<void>;
  sendMessage: (content: string) => void;
  toggleNav: () => void;
  getMessageTracing: (messageId: string) => DebugOutput[];
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Set of already processed message IDs to prevent duplicates
const processedMessageIds = new Set<string>();

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChat, setCurrentChat] = useState<ChatWithMessages | null>(null);
  const [messageTracing, setMessageTracing] = useState<MessageTracing>({});
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);

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
      
      if (data.debug) {
        // Handle debug output - store it with the current message
        const debugOutput = {
          content: data.debug,
          timestamp: new Date().toISOString(),
        };
        
        // Always associate debug output with the current assistant message being generated
        setMessageTracing(prev => {
          // If we have a currentMessageId, store under that, otherwise use a temporary ID
          const targetMessageId = currentMessageId || 'pending';
          const existingTracing = prev[targetMessageId] || [];
          
          return {
            ...prev,
            [targetMessageId]: [...existingTracing, debugOutput]
          };
        });
      } else if (data.role && data.message) {
        // Handle new message
        const newMessage: Message = {
          id: messageId,
          role: data.role,
          content: data.message,
          created_at: new Date().toISOString()
        };
        
        if (data.role === 'assistant') {
          // Mark processing as complete when receiving assistant message
          setIsProcessing(false);
          
          // For assistant messages, update the currentMessageId
          // AND migrate any debug messages from the 'pending' bucket
          setCurrentMessageId(messageId);
          
          // Transfer any pending tracing data to this message ID
          setMessageTracing(prev => {
            const pendingTracing = prev['pending'] || [];
            
            return {
              ...prev,
              [messageId]: pendingTracing,
              // Clear the pending bucket after transferring
              'pending': []
            };
          });
        }
        
        setCurrentChat(prev => {
          if (!prev) return null;
          
          // Check if we already have this message
          const messageExists = prev.messages.some(msg => msg.id === newMessage.id);
          if (messageExists) {
            return prev;
          }
          
          return {
            ...prev,
            messages: [...prev.messages, newMessage]
          };
        });
        
        // If it's an assistant message, update the chat list without refreshing the whole chat
        if (data.role === 'assistant') {
          // Only refresh the chat list, not the entire chat with messages
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
      setIsProcessing(false); // Ensure processing state is reset on error
    };
    
    newSocket.onclose = (event) => {
      console.log('WebSocket connection closed', event.code, event.reason);
      setSocketConnected(false);
      setIsProcessing(false); // Ensure processing state is reset on close
      
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
      
      // Reset current message ID
      setCurrentMessageId(null);
      
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
      
      // Clear message tracing for new chat - we don't want to show tracing for loaded messages
      setMessageTracing({});
      
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
    if (isProcessing) {
      console.log('Already processing a message, ignoring new message');
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
                setIsProcessing(false);
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
    
    // Reset the current message ID when sending a new message
    setCurrentMessageId(null);
    
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
    
    // Reset the pending tracing data
    setMessageTracing(prev => ({
      ...prev,
      pending: []
    }));
    
    // Send message to WebSocket
    socketToUse.send(JSON.stringify({
      message: content
    }));
  };

  // Toggle side navigation
  const toggleNav = () => {
    setIsNavOpen(prev => !prev);
  };

  // Get tracing data for a specific message
  const getMessageTracing = (messageId: string): DebugOutput[] => {
    return messageTracing[messageId] || messageTracing['latest'] || [];
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
      toggleNav,
      getMessageTracing
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