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
    <div className="flex justify-center mb-4">
      <svg 
        width="120" 
        height="120" 
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
    <div className="flex flex-col items-center justify-center h-full">
      <div className="bg-white/70 backdrop-blur-sm rounded-lg shadow-lg max-w-4xl w-full mx-auto px-6 py-4 text-center">
        <FrogLogo />
        
        <h2 className="text-2xl font-bold text-frog-dark mb-2">
          Welcome to FrOG
        </h2>
        
        <div className="text-lg text-frog-dark/80 font-semibold mb-2">
          Framework of Open GraphRAG
        </div>
        
        <p className="text-gray-700 mx-auto max-w-2xl mb-4">
          Ask questions and get answers based on our knowledge graph. FrOG searches for entities,
          constructs SPARQL queries, and provides detailed explanations of its reasoning process.
        </p>
        
        <div className="bg-frog-light/50 p-4 rounded-lg max-w-3xl mx-auto border-2 border-frog-DEFAULT lily-pad">
          <h3 className="font-semibold text-frog-dark mb-2">Try asking:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-left">
            <div className="flex items-center">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0"></span>
              <span>"Who is the current president of France?"</span>
            </div>
            <div className="flex items-center">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0"></span>
              <span>"What is the capital of Japan and what is its population?"</span>
            </div>
            <div className="flex items-center">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0"></span>
              <span>"List the spouses of Albert Einstein"</span>
            </div>
            <div className="flex items-center">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0"></span>
              <span>"Which mountains in the Himalayas are higher than 8000 meters?"</span>
            </div>
            <div className="flex items-center">
              <span className="inline-block w-2 h-2 bg-frog-dark rounded-full mr-2 flex-shrink-0"></span>
              <span>"What books did Isaac Asimov write?"</span>
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