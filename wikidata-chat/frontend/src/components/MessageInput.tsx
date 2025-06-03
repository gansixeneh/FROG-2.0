// frontend/src/components/MessageInput.tsx
import React, { useState, useEffect } from 'react';
import { useChat } from '../context/ChatContext';
import { API_HOST } from '../config/api';

const MessageInput: React.FC = () => {
  const [message, setMessage] = useState('');
  const [dots, setDots] = useState(1);
  const { sendMessage, currentChat, isProcessing, settings } = useChat();
  
  // Animate dots when processing
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isProcessing) {
      interval = setInterval(() => {
        setDots(prevDots => {
          // Cycle from 1 to 3 dots
          return prevDots >= 3 ? 1 : prevDots + 1;
        });
      }, 500); // Change dots every 500ms
    } else {
      // Reset to 1 dot when not processing
      setDots(1);
    }
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isProcessing]);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isProcessing) return;
    
    sendMessage(message);
    setMessage('');
  };
  
  // Generate the animated thinking text
  const getThinkingText = () => {
    return `FrOG is thinking${'.'.repeat(dots)}`;
  };
  
  // Frog lily pad
  const LilyPad = () => (
    <div className="absolute -top-6 left-1/2 transform -translate-x-1/2">
      <svg width="60" height="10" viewBox="0 0 60 10">
        <ellipse cx="30" cy="5" rx="30" ry="5" fill="#4ade80" opacity="0.3" />
      </svg>
    </div>
  );
  
  return (
    <div className="border-t border-frog-dark/10 bg-white p-4 fixed bottom-0 left-0 right-0 bg-opacity-90 backdrop-blur-sm">
      <form onSubmit={handleSubmit} className="flex items-center mx-auto max-w-4xl relative">
        <LilyPad />
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={isProcessing ? getThinkingText() : `Ask FrOG a question about ${
            settings.knowledgeSource === 'wikidata' ? 'Wikidata' : 
            settings.knowledgeSource === 'curriculum' ? 'Curriculum' :
            settings.knowledgeSource === 'legal' ? 'Legal Documents' : 'GESIS Scholarly Articles'
          }...`}
          className="flex-grow h-12 px-4 border-2 border-frog-DEFAULT rounded-full focus:outline-none focus:ring-2 focus:ring-frog-dark focus:border-transparent shadow-md"
          disabled={!currentChat || isProcessing}
        />
        <button
          type="submit"
          className={`${
            isProcessing ? 'bg-frog-light cursor-not-allowed' : 'bg-frog-dark hover:bg-frog-dark/90'
          } text-white h-12 w-12 rounded-full ml-3 transition-colors disabled:bg-frog-light flex items-center justify-center shadow-lg`}
          disabled={!message.trim() || !currentChat || isProcessing}
        >
          {isProcessing ? (
            <div className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin"></div>
          ) : (
            <svg
              className="w-5 h-5"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
          )}
        </button>
        
        {/* Decorative lily pads */}
        <div className="absolute -bottom-3 left-1/4 w-8 h-2 bg-frog-DEFAULT/20 rounded-full"></div>
        <div className="absolute -bottom-4 right-1/3 w-12 h-3 bg-frog-DEFAULT/20 rounded-full"></div>
      </form>
      
      {/* Footer with FrOG credit */}
      <div className="text-center text-frog-dark/50 text-xs mt-2">
        FrOG: Framework of Open GraphRAG | Connected to: {
          settings.knowledgeSource === 'wikidata' ? 'Wikidata' : 
          settings.knowledgeSource === 'curriculum' ? 'Curriculum (https://generous-lark-duly.ngrok-free.app/curi/query)' :
          settings.knowledgeSource === 'legal' ? 'Legal Document KB (https://generous-lark-duly.ngrok-free.app/modified-lex2kg/query)' :
          'GESIS Scholarly KB (https://generous-lark-duly.ngrok-free.app/gesis/query)'
        }
      </div>
    </div>
  );
};

export default MessageInput;