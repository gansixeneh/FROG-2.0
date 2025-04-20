// frontend/src/components/MessageInput.tsx
import React, { useState } from 'react';
import { useChat } from '../context/ChatContext';

const MessageInput: React.FC = () => {
  const [message, setMessage] = useState('');
  const { sendMessage, currentChat, isProcessing } = useChat();
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isProcessing) return;
    
    sendMessage(message);
    setMessage('');
  };
  
  return (
    <div className="border-t border-gray-200 bg-white p-4 fixed bottom-0 left-0 right-0">
      <form onSubmit={handleSubmit} className="flex items-center mx-auto max-w-4xl">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={isProcessing ? "Waiting for response..." : "Ask a question..."}
          className="flex-grow h-12 px-4 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={!currentChat || isProcessing}
        />
        <button
          type="submit"
          className={`${
            isProcessing ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'
          } text-white h-12 w-12 rounded-full ml-3 transition-colors disabled:bg-gray-400 flex items-center justify-center shadow-md`}
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
      </form>
    </div>
  );
};

export default MessageInput;