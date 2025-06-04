// frontend/src/components/SideNav.tsx
import React from 'react';
import { useChat } from '../context/ChatContext';
import { formatDistanceToNow } from 'date-fns';

const SideNav: React.FC = () => {
  const { chats, isNavOpen, loadChat, currentChat, startNewChat, toggleNav } = useChat();
  
  return (
    <div 
      className={`fixed inset-y-0 left-0 transform ${
        isNavOpen ? 'translate-x-0' : '-translate-x-full'
      } w-64 bg-gradient-to-b from-frog-dark to-frog-dark/90 text-white transition-transform duration-300 ease-in-out z-20 pt-16`}
    >
      {/* Add close button */}
      <button
        onClick={toggleNav}
        className="absolute top-4 left-4 p-2 rounded-md text-white hover:text-frog-accent hover:bg-frog-dark/50 focus:outline-none"
        aria-label="Close sidebar"
      >
        <svg 
          className="h-6 w-6" 
          xmlns="http://www.w3.org/2000/svg" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M6 18L18 6M6 6l12 12" 
          />
        </svg>
      </button>
      
      <div className="p-4 pb-20 h-full overflow-hidden flex flex-col">
        <button
          onClick={startNewChat}
          className="w-full py-2 px-4 bg-frog-accent text-frog-dark rounded-md mb-6 flex items-center justify-center font-semibold hover:bg-white transition-colors flex-shrink-0"
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
        
        {/* Frog decoration */}
        <div className="flex justify-center mb-6 flex-shrink-0">
          <div className="relative">
            <svg width="80" height="40" viewBox="0 0 180 100">
              <path 
                d="M10,90 Q90,110 170,90" 
                fill="none" 
                stroke="#4ade80" 
                strokeWidth="5" 
                strokeLinecap="round"
              />
              <circle cx="90" cy="90" r="5" fill="#a6e9a6" />
              <circle cx="70" cy="85" r="5" fill="#a6e9a6" />
              <circle cx="110" cy="85" r="5" fill="#a6e9a6" />
              <circle cx="50" cy="88" r="3" fill="#a6e9a6" />
              <circle cx="130" cy="88" r="3" fill="#a6e9a6" />
            </svg>
          </div>
        </div>
        
        <h2 className="text-sm font-semibold text-frog-accent uppercase tracking-wider mb-3 flex-shrink-0">
          Chat History
        </h2>
        
        <div className="flex-1 overflow-y-auto">
          <div className="space-y-2">
            {chats.length === 0 ? (
              <div className="text-frog-light text-sm p-2">No chat history</div>
            ) : (
              chats.map(chat => (
                <button
                  key={chat.id}
                  onClick={() => loadChat(chat.id)}
                  className={`w-full text-left py-2 px-3 rounded-md transition-colors ${
                    currentChat?.id === chat.id 
                      ? 'bg-frog-DEFAULT/30 border-l-4 border-frog-accent' 
                      : 'text-frog-light hover:bg-frog-DEFAULT/10 border-l-4 border-transparent'
                  } lily-pad`}
                >
                  <div className="text-sm font-medium truncate">{chat.title}</div>
                  <div className="text-xs text-frog-light/70 mt-1">
                    {formatDistanceToNow(new Date(chat.updated_at), { addSuffix: true })}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
      
      {/* Footer with FrOG brand */}
      <div className="absolute bottom-0 left-0 right-0 p-4 text-center text-frog-light/70 text-xs">
        <p>FrOG: Framework of Open GraphRAG</p>
        <p className="mt-1">© 2025 FROG-2.0</p>
      </div>
    </div>
  );
};

export default SideNav;