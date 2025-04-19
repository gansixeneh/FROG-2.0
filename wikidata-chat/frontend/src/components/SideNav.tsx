// frontend/src/components/SideNav.tsx
import React from 'react';
import { useChat } from '../context/ChatContext';
import { formatDistanceToNow } from 'date-fns';

const SideNav: React.FC = () => {
  const { chats, isNavOpen, loadChat, currentChat, startNewChat } = useChat();
  
  return (
    <div 
      className={`fixed inset-y-0 left-0 transform ${
        isNavOpen ? 'translate-x-0' : '-translate-x-full'
      } w-64 bg-gray-800 text-white transition-transform duration-300 ease-in-out z-20 pt-16`}
    >
      <div className="p-4">
        <button
          onClick={startNewChat}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-md mb-4 flex items-center justify-center"
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
        
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Chat History
        </h2>
        
        <div className="space-y-1">
          {chats.length === 0 ? (
            <div className="text-gray-400 text-sm p-2">No chat history</div>
          ) : (
            chats.map(chat => (
              <button
                key={chat.id}
                onClick={() => loadChat(chat.id)}
                className={`w-full text-left py-2 px-3 rounded-md transition-colors ${
                  currentChat?.id === chat.id 
                    ? 'bg-gray-700 text-white' 
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <div className="text-sm font-medium truncate">{chat.title}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {formatDistanceToNow(new Date(chat.updated_at), { addSuffix: true })}
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
};