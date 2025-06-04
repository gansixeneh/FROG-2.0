// frontend/src/context/ChatContext.tsx
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import {
  Chat,
  ChatWithMessages,
  Message,
  AgentSettings,
} from "../types";
import { fetchChats, fetchChat, createChat, sendMessage as apiSendMessage } from "../utils/api";
import { pusherService, PusherMessage } from "../services/pusherService";
import { API_HOST } from "../config/api";

interface ChatContextType {
  chats: Chat[];
  currentChat: ChatWithMessages | null;
  isNavOpen: boolean;
  isLoading: boolean;
  isProcessing: boolean;
  settings: AgentSettings;
  pusherStatus: any;
  loadChat: (chatId: string) => Promise<void>;
  startNewChat: () => Promise<void>;
  sendMessage: (content: string) => void;
  toggleNav: () => void;
  updateSettings: (newSettings: AgentSettings) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Set of already processed message IDs to prevent duplicates
const processedMessageIds = new Set<string>();

export const ChatProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChat, setCurrentChat] = useState<ChatWithMessages | null>(null);
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pusherStatus, setPusherStatus] = useState(() => pusherService.getConnectionStatus());

  // Initialize settings from localStorage or use defaults
  const [settings, setSettings] = useState<AgentSettings>(() => {
    const defaultSettings: AgentSettings = {
      useVerbalization: true,
      useGoogleSearch: true,
      useTranslation: true,
      knowledgeSource: "wikidata",
    };

    try {
      const savedSettings = localStorage.getItem("frog-settings");
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        // Merge saved settings with defaults to ensure all properties are present
        return {
          ...defaultSettings,
          ...parsed,
        };
      }
    } catch (error) {
      console.error("Error loading settings from localStorage:", error);
    }
    
    return defaultSettings;
  });

  // Monitor Pusher connection status
  useEffect(() => {
    const interval = setInterval(() => {
      const status = pusherService.getConnectionStatus();
      setPusherStatus(status);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

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
        console.error("Error loading chats:", error);
        setIsLoading(false);
      }
    };

    loadChats();
  }, []);

  // Handle Pusher message processing
  const handlePusherMessage = (data: PusherMessage) => {
    const messageId = data.message_id || `fallback-${Date.now()}-${Math.random()}`;

    // Skip if we've already processed this message
    if (processedMessageIds.has(messageId)) {
      return;
    }

    // Add to processed message set
    processedMessageIds.add(messageId);

    // Handle debug message (system message with debug content)
    if (data.debug) {
      const newMessage: Message = {
        id: messageId,
        role: "system",
        content: data.debug,
        created_at: new Date().toISOString(),
      };

      setCurrentChat((prev) => {
        if (!prev) {
          return null;
        }
        const updatedChat = {
          ...prev,
          messages: [...prev.messages, newMessage],
        };

        // Force immediate scroll for real-time feedback
        setTimeout(() => {
          const messagesEndElement = document.getElementById("messages-end");
          if (messagesEndElement) {
            messagesEndElement.scrollIntoView({ behavior: "smooth" });
          }
        }, 0);

        return updatedChat;
      });
      return;
    }
    // Handle regular message with possible visualization files
    if (data.role && data.message) {
      const newMessage: Message = {
        id: messageId,
        role: data.role,
        content: data.message,
        created_at: new Date().toISOString(),
        visualization_files: data.visualization_files || undefined,
      };

      setCurrentChat((prev) => {
        if (!prev) {
          return null;
        }
        return {
          ...prev,
          messages: [...prev.messages, newMessage],
        };
      });

      if (data.role === "assistant") {
        setIsProcessing(false);
        refreshChatsList();
      }
      return;
    }

    // Log unhandled message type for debugging purposes
    if (process.env.NODE_ENV === 'development') {
      console.warn("Unhandled Pusher message type:", data);
    }
  };

  // Setup Pusher for current chat with retry logic
  const setupPusher = (chatId: string) => {
    // Clear the set of processed message IDs when setting up a new channel
    clearProcessedMessageIds();

    const callbacks = {
      onDebugMessage: (data: PusherMessage) => {
        handlePusherMessage(data);
      },
      onSystemMessage: (data: PusherMessage) => {
        handlePusherMessage(data);
      },
      onChatMessage: (data: PusherMessage) => {
        handlePusherMessage(data);
      },
      onMessage: (data: PusherMessage) => {
        handlePusherMessage(data);
      },
    };

    // Try to subscribe, with retry if connection isn't ready
    const attemptSubscription = () => {
      pusherService.subscribeToChat(chatId, callbacks);
    };

    attemptSubscription();

    // If connection isn't ready, retry after a delay
    const status = pusherService.getConnectionStatus();
    if (!status.isConnected) {
      setTimeout(() => {
        const newStatus = pusherService.getConnectionStatus();
        if (newStatus.isConnected) {
          attemptSubscription();
        }
      }, 2000);
    }
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
      chatData.messages.forEach((msg) => {
        processedMessageIds.add(msg.id);
      });

      // Setup Pusher for this chat
      setupPusher(chatId);

      // Close sidebar on mobile after selecting a chat
      setIsNavOpen(false);
      setIsLoading(false);
    } catch (error) {
      console.error("Error loading chat:", error);
      setIsLoading(false);
    }
  };

  // Refresh just the chats list without affecting the connection
  const refreshChatsList = async () => {
    try {
      const chatList = await fetchChats();
      setChats(chatList);
    } catch (error) {
      console.error("Error refreshing chats list:", error);
    }
  };

  // Start a new chat
  const startNewChat = async () => {
    try {
      setIsLoading(true);
      const newChat = await createChat();

      // Add new chat to list
      setChats((prev) => [newChat, ...prev]);

      // Load the new chat
      await loadChat(newChat.id);

      setIsNavOpen(false);
      setIsLoading(false);
    } catch (error) {
      console.error("Error creating new chat:", error);
      setIsLoading(false);
    }
  };

  // Send a message
  const sendMessage = (content: string) => {
    // Don't allow sending if already processing a message
    if (isProcessing || !currentChat) {
      return;
    }

    setIsProcessing(true);

    // Create a temporary message ID
    const tempId = `temp-${Date.now()}`;

    // Add to processed set to prevent duplication when real message comes back
    processedMessageIds.add(tempId);

    // Add user message to UI immediately
    const newMessage: Message = {
      id: tempId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setCurrentChat((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        messages: [...prev.messages, newMessage],
      };
    });

    // Send message via API
    apiSendMessage(currentChat.id, content, settings)
      .then((response) => {
        // Message sent successfully
      })
      .catch((error) => {
        console.error("Error sending message:", error);
        setIsProcessing(false);
        alert("Error sending message. Please try again.");
      });
  };
  // Toggle side navigation
  const toggleNav = () => {
    setIsNavOpen((prev) => !prev);
  };

  // Update settings
  const updateSettings = (newSettings: AgentSettings) => {
    setSettings(newSettings);
    try {
      localStorage.setItem("frog-settings", JSON.stringify(newSettings));
    } catch (error) {
      console.error("Error saving settings to localStorage:", error);
    }
  };

  // Cleanup Pusher connection on unmount
  useEffect(() => {
    return () => {
      pusherService.disconnect();
    };
  }, []);

  return (
    <ChatContext.Provider
      value={{
        chats,
        currentChat,
        isNavOpen,
        isLoading,
        isProcessing,
        settings,
        pusherStatus,
        loadChat,
        startNewChat,
        sendMessage,
        toggleNav,
        updateSettings,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
