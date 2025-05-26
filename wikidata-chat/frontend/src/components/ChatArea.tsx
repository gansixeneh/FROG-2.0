// frontend/src/components/ChatArea.tsx
import React, { useEffect, useRef } from "react";
import { useChat } from "../context/ChatContext";
import ChatMessage from "./ChatMessage";
import SystemMessageGroup from "./SystemMessageGroup";
import { Message } from "../types";
import FrogLogo from './FrogLogo';

// Define a type for our processed messages
type ProcessedMessageItem = 
  | { type: "regular"; message: Message }
  | { type: "systemGroup"; messages: Message[] };

const ChatArea: React.FC = () => {
  const { currentChat, isLoading, settings } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    <div className="flex flex-col items-center justify-start min-h-0 py-4 sm:py-8 max-h-full overflow-y-auto">
      <div className="bg-white/70 backdrop-blur-sm rounded-lg shadow-lg max-w-4xl w-full mx-auto px-4 py-4 sm:px-6 sm:py-6 text-center mb-8">
        <div className="flex justify-center">
          <FrogLogo width={120} height={120} />
        </div>
        
        <h2 className="text-xl sm:text-2xl font-bold text-frog-dark mb-2">
          Welcome to FrOG
        </h2>
        
        <div className="text-base sm:text-lg text-frog-dark/80 font-semibold mb-2">
          Framework of Open GraphRAG
        </div>
        
        <p className="text-sm sm:text-base text-gray-700 mx-auto max-w-2xl mb-4">
          Ask questions and get answers based on our knowledge graph. FrOG searches for entities,
          constructs SPARQL queries, and provides detailed explanations of its reasoning process.
        </p>
        
        <div className="bg-frog-light/50 p-3 sm:p-4 rounded-lg max-w-3xl mx-auto border-2 border-frog-DEFAULT lily-pad">
          <h3 className="font-semibold text-frog-dark mb-2 text-sm sm:text-base">Try asking:</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 text-left text-xs sm:text-sm">
            <div className="flex items-start">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0 mt-1"></span>
              <span>"Who is the current president of France?"</span>
            </div>
            <div className="flex items-start">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0 mt-1"></span>
              <span>"What is the capital of Japan and what is its population?"</span>
            </div>
            <div className="flex items-start">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0 mt-1"></span>
              <span>"List the spouses of Albert Einstein"</span>
            </div>
            <div className="flex items-start">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0 mt-1"></span>
              <span>"Which mountains in the Himalayas are higher than 8000 meters?"</span>
            </div>
            <div className="flex items-start lg:col-span-2 lg:justify-center">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0 mt-1"></span>
              <span>"What books did Isaac Asimov write?"</span>
            </div>
          </div>
          
          {/* Settings indicator */}
          <div className="mt-3 sm:mt-4 pt-3 border-t border-frog-dark/20">
            <div className="text-xs sm:text-sm text-frog-dark/70 flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
              <span className="font-medium">Current Settings:</span>
              <div className="flex flex-wrap gap-1 sm:gap-2 justify-center">
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                  settings.useVerbalization ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                }`}>
                  {settings.useVerbalization ? 'Verbalization ON' : 'SPARQL Only'}
                </span>
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                  settings.useGoogleSearch ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {settings.useGoogleSearch ? 'Google Search ON' : 'Wikidata Only'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-t-4 border-frog-dark"></div>
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
      {/* Background lily pad */}
      <div className="absolute top-20 left-1/2 transform -translate-x-1/2 w-24 h-24 rounded-full bg-frog-light/30 -z-10"></div>
      
      {/* Messages */}
      <div className="flex flex-col space-y-4 relative">
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

        <div ref={messagesEndRef} id="messages-end" />
      </div>
    </div>
  );
};

export default ChatArea;