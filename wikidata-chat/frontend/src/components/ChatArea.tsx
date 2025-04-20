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

  const FrogLogo = () => (
    <div className="flex justify-center mb-8">
      <svg 
        width="160" 
        height="160" 
        viewBox="0 0 300 300" 
        className="frog-logo"
      >
        {/* Main frog body - light green */}
        <circle cx="150" cy="150" r="100" fill="#4ade80" stroke="#166534" strokeWidth="6" />
        
        {/* Eyes */}
        <circle cx="110" cy="120" r="25" fill="white" stroke="#166534" strokeWidth="3" />
        <circle cx="110" cy="120" r="12" fill="#166534" />
        <circle cx="190" cy="120" r="25" fill="white" stroke="#166534" strokeWidth="3" />
        <circle cx="190" cy="120" r="12" fill="#166534" />
        
        {/* Cheeks with knowledge graph icons */}
        <circle cx="90" cy="160" r="18" fill="#166534" opacity="0.7" />
        <circle cx="210" cy="160" r="18" fill="#166534" opacity="0.7" />
        
        {/* Network nodes in cheeks (simplified) */}
        <circle cx="90" cy="160" r="12" fill="#a6e9a6" />
        <circle cx="210" cy="160" r="12" fill="#a6e9a6" />
        
        {/* Smile */}
        <path d="M120,180 Q150,200 180,180" stroke="#166534" strokeWidth="6" fill="none" />
        
        {/* Decorative nodes on the knowledge graph in the cheeks */}
        <circle cx="85" cy="155" r="2" fill="white" />
        <circle cx="95" cy="155" r="2" fill="white" />
        <circle cx="90" cy="165" r="2" fill="white" />
        
        <circle cx="205" cy="155" r="2" fill="white" />
        <circle cx="215" cy="155" r="2" fill="white" />
        <circle cx="210" cy="165" r="2" fill="white" />
        
        {/* "Network" lines in cheeks */}
        <line x1="85" y1="155" x2="95" y2="155" stroke="white" strokeWidth="1" />
        <line x1="85" y1="155" x2="90" y2="165" stroke="white" strokeWidth="1" />
        <line x1="95" y1="155" x2="90" y2="165" stroke="white" strokeWidth="1" />
        
        <line x1="205" y1="155" x2="215" y2="155" stroke="white" strokeWidth="1" />
        <line x1="205" y1="155" x2="210" y2="165" stroke="white" strokeWidth="1" />
        <line x1="215" y1="155" x2="210" y2="165" stroke="white" strokeWidth="1" />
      </svg>
    </div>
  );

  const renderWelcomeScreen = () => (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 py-8 bg-white/70 backdrop-blur-sm rounded-lg shadow-lg max-w-2xl mx-auto mt-6">
      <FrogLogo />
      
      <h2 className="text-3xl font-bold text-frog-dark mb-4">
        Welcome to FrOG
      </h2>
      
      <div className="text-xl text-frog-dark/80 font-semibold mb-4">
        Framework of Open GraphRAG
      </div>
      
      <p className="text-gray-700 max-w-md mb-6">
        Ask questions and get answers based on our knowledge graph. FrOG searches for entities,
        constructs SPARQL queries, and provides detailed explanations of its reasoning process.
      </p>
      
      <div className="mt-6 bg-frog-light/50 p-6 rounded-lg max-w-md w-full border-2 border-frog-DEFAULT lily-pad">
        <h3 className="font-semibold text-frog-dark mb-3 text-lg">Try asking:</h3>
        <ul className="text-left text-frog-dark space-y-3">
          <li className="flex items-center">
            <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2"></span>
            "Who is the current president of France?"
          </li>
          <li className="flex items-center">
            <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2"></span>
            "What is the capital of Japan and what is its population?"
          </li>
          <li className="flex items-center">
            <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2"></span>
            "List the spouses of Albert Einstein"
          </li>
          <li className="flex items-center">
            <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2"></span>
            "Which mountains in the Himalayas are higher than 8000 meters?"
          </li>
          <li className="flex items-center">
            <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2"></span>
            "What books did Isaac Asimov write?"
          </li>
        </ul>
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

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default ChatArea;