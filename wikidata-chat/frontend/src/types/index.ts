// frontend/src/types/index.ts
export interface Chat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  last_message?: Message;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface ChatWithMessages extends Chat {
  messages: Message[];
}

export interface DebugOutput {
  content: string;
  timestamp: string;
  id?: string; // Optional ID to track debug outputs
}

// Map of message IDs to their associated tracing data
export interface MessageTracing {
  [messageId: string]: DebugOutput[];
}