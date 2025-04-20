// frontend/src/components/ChatArea.tsx
import React, { useEffect, useRef } from "react";
import { useChat } from "../context/ChatContext";
import ChatMessage from "./ChatMessage";
import SystemMessageGroup from "./SystemMessageGroup";
import { Message } from "../types";

// Define a type for our processed messages
type ProcessedMessageItem = 
  | { type: "regular"; message: Message }
  | { type: "systemGroup"; messages: Message[] };

const ChatArea: React.FC = () => {
  const { currentChat, isLoading } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    console.log("Current chat:", currentChat);
  }, [currentChat]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentChat?.messages]);

  // Process messages to group consecutive system messages
  const processMessages = (): ProcessedMessageItem[] => {
    if (!currentChat?.messages.length) return [];

    const processedMessages: ProcessedMessageItem[] = [];
    let currentSystemMessages: Message[] = [];

    currentChat.messages.forEach((message) => {
      if (message.role === "system") {
        // Add to the current group of system messages
        currentSystemMessages.push(message);
      } else {
        // If we have accumulated system messages, add them as a group
        if (currentSystemMessages.length > 0) {
          processedMessages.push({
            type: "systemGroup",
            messages: [...currentSystemMessages],
          });
          currentSystemMessages = [];
        }

        // Add the regular message
        processedMessages.push({
          type: "regular",
          message,
        });
      }
    });

    // Don't forget any remaining system messages
    if (currentSystemMessages.length > 0) {
      processedMessages.push({
        type: "systemGroup",
        messages: [...currentSystemMessages],
      });
    }

    return processedMessages;
  };

  const renderWelcomeScreen = () => (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="mb-6">
        <svg
          className="mx-auto h-16 w-16 text-blue-600"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>
      <h2 className="text-2xl font-bold text-gray-800 mb-2">
        Welcome to Wikidata Agent
      </h2>
      <p className="text-gray-600 max-w-md">
        Ask questions and get answers from Wikidata. I can search for entities,
        construct SPARQL queries, and provide detailed explanations of my
        reasoning process.
      </p>
      <div className="mt-8 bg-blue-50 p-4 rounded-md max-w-md">
        <h3 className="font-semibold text-blue-800 mb-2">Try asking:</h3>
        <ul className="text-left text-blue-700 space-y-2">
          <li>"Who is the current president of France?"</li>
          <li>"What is the capital of Japan and what is its population?"</li>
          <li>"List the spouses of Albert Einstein"</li>
          <li>
            "Which mountains in the Himalayas are higher than 8000 meters?"
          </li>
          <li>"What books did Isaac Asimov write?"</li>
        </ul>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700"></div>
      </div>
    );
  }

  // Show welcome screen if there's no current chat OR if current chat has no messages
  if (!currentChat || (currentChat && currentChat.messages.length === 0)) {
    return renderWelcomeScreen();
  }

  // Process messages to group system messages
  const processedMessages = processMessages();

  return (
    <div className="p-4 pb-20 h-full overflow-y-auto mx-auto max-w-4xl">
      {/* Messages */}
      <div className="flex flex-col space-y-4">
        {processedMessages.map((item, index) => {
          if (item.type === "systemGroup") {
            return (
              <SystemMessageGroup 
                key={`system-group-${index}`} 
                messages={item.messages} 
              />
            );
          } else {
            return (
              <ChatMessage 
                key={item.message.id} 
                message={item.message} 
              />
            );
          }
        })}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatArea;