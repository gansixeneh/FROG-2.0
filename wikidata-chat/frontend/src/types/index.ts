// frontend/src/types/index.ts
export interface Chat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  last_message?: Message;
}

export interface VisualizationFile {
  content: string;
  file_name: string;
}

export interface VisualizationFilesContent {
  json?: VisualizationFile;
  mermaid?: VisualizationFile;
  ttl?: VisualizationFile;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  visualization_files?: VisualizationFilesContent;
}

export interface ChatWithMessages extends Chat {
  messages: Message[];
}

// Legacy type for backward compatibility
export interface VisualizationFiles {
  json: boolean;
  mermaid: boolean;
  ttl: boolean;
}

export interface AgentSettings {
  useVerbalization: boolean;
  useGoogleSearch: boolean;
}