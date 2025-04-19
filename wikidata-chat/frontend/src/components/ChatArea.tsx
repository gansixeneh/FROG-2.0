// frontend/src/components/ChatArea.tsx
import React, { useEffect, useRef, useState } from 'react';
import { useChat } from '../context/ChatContext';
import ChatMessage from './ChatMessage';

const ChatArea: React.FC = () => {
  const { currentChat, debugOutput, isLoading } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showDebug, setShowDebug] = useState(false);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentChat?.messages, debugOutput]);
  
  const renderDebugOutput = () => (
    <div className="bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm max-h-[50vh] overflow-y-auto">
      <pre className="whitespace-pre-wrap">
        {debugOutput.map((debug, index) => (
          <div key={index} className="mb-2">
            {debug.content}
          </div>
        ))}
      </pre>
    </div>
  );
  
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
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome to Wikidata Agent</h2>
      <p className="text-gray-600 max-w-md">
        Ask questions and get answers from Wikidata. I can search for entities, construct SPARQL queries, and provide
        detailed explanations of my reasoning process.
      </p>
      <div className="mt-8 bg-blue-50 p-4 rounded-md max-w-md">
        <h3 className="font-semibold text-blue-800 mb-2">Try asking:</h3>
        <ul className="text-left text-blue-700 space-y-2">
          <li>"Who is the current president of France?"</li>
          <li>"What is the capital of Japan and what is its population?"</li>
          <li>"List the spouses of Albert Einstein"</li>
          <li>"Which mountains in the Himalayas are higher than 8000 meters?"</li>
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
  
  if (!currentChat) {
    return renderWelcomeScreen();
  }
  
  return (
    <div className="p-4 pb-20 h-full overflow-y-auto">
      {/* Messages */}
      <div className="flex flex-col space-y-4">
        {currentChat.messages.map(message => (
          <ChatMessage key={message.id} message={message} />
        ))}
        
        {/* Debug toggle */}
        {debugOutput.length > 0 && (
          <div className="mx-auto">
            <button
              onClick={() => setShowDebug(prev => !prev)}
              className="px-3 py-1 bg-gray-200 text-gray-700 rounded-md text-sm hover:bg-gray-300"
            >
              {showDebug ? 'Hide Agent Tracing' : 'Show Agent Tracing'}
            </button>
          </div>
        )}
        
        {/* Debug output */}
        {showDebug && debugOutput.length > 0 && renderDebugOutput()}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};