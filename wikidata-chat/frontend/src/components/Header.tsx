// frontend/src/components/Header.tsx
import React from 'react';
import { useChat } from '../context/ChatContext';
import { API_HOST } from '../config/api';

const Header: React.FC = () => {
  const { toggleNav, isNavOpen, startNewChat } = useChat();
  
  // Frog logo SVG - simplified version for the header
  const FrogLogo = () => (
    <svg 
      width="36" 
      height="36" 
      viewBox="0 0 200 200" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className="frog-logo"
    >
      {/* Stylized frog head */}
      <circle cx="100" cy="100" r="80" fill="#4ade80" />
      <circle cx="70" cy="80" r="20" fill="white" />
      <circle cx="70" cy="80" r="10" fill="#166534" />
      <circle cx="130" cy="80" r="20" fill="white" />
      <circle cx="130" cy="80" r="10" fill="#166534" />
      <path d="M80 120 Q100 140 120 120" stroke="#166534" strokeWidth="6" fill="none" />
    </svg>
  );
  
  return (
    <header className="bg-gradient-to-r from-frog-dark via-frog-DEFAULT to-frog-dark shadow-md border-b border-frog-dark fixed top-0 left-0 right-0 z-10">
      <div className="flex items-center justify-between px-4 py-2">
        <div className="flex items-center">
          <button 
            onClick={toggleNav}
            className="p-2 rounded-md text-white hover:bg-frog-dark/50 focus:outline-none"
            aria-label="Toggle sidebar"
          >
            <svg 
              className="h-6 w-6" 
              xmlns="http://www.w3.org/2000/svg" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              {isNavOpen ? (
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M6 18L18 6M6 6l12 12" 
                />
              ) : (
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M4 6h16M4 12h16M4 18h16" 
                />
              )}
            </svg>
          </button>
          
          <div className="flex items-center ml-2">
            <FrogLogo />
            <div className="ml-3">
              <h1 className="text-xl font-bold text-white">
                FrOG
              </h1>
              <div className="text-xs text-frog-accent font-semibold">
                Framework of Open GraphRAG
              </div>
            </div>
          </div>
        </div>
        
        <button
          onClick={startNewChat}
          className="px-4 py-2 bg-frog-accent text-frog-dark rounded-full hover:bg-white focus:outline-none font-semibold transition-colors shadow-md flex items-center"
        >
          <svg
            className="w-5 h-5 mr-2"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Chat
        </button>
      </div>
    </header>
  );
};

export default Header;