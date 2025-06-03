// frontend/src/components/Header.tsx
import React, { useState } from 'react';
import { useChat } from '../context/ChatContext';
import { API_HOST } from '../config/api';
import Settings from './Settings';
import FrogLogo from './FrogLogo';
import JenaLogsModal from './JenaLogsModal'; // Add this import

const Header: React.FC = () => {
  const { toggleNav, isNavOpen, startNewChat, pusherStatus, settings, updateSettings } = useChat();
  const [showSettings, setShowSettings] = useState(false);
  const [showJenaLogs, setShowJenaLogs] = useState(false); // Add this state
  
  const getStatusColor = (isConnected: boolean) => {
    return isConnected ? 'bg-green-400' : 'bg-red-400';
  };
  
  const getConnectionStateText = (state: string) => {
    switch (state) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting';
      case 'disconnected': return 'Disconnected';
      case 'unavailable': return 'Unavailable';
      default: return state;
    }
  };

  // Handler for changing the knowledge source
  const toggleKnowledgeSource = () => {
    const sourceOrder = ['wikidata', 'curriculum', 'legal', 'gesis'];
    const currentIndex = sourceOrder.indexOf(settings.knowledgeSource);
    const nextIndex = (currentIndex + 1) % sourceOrder.length;
    updateSettings({
      ...settings,
      knowledgeSource: sourceOrder[nextIndex]
    });
  };
  
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
            <FrogLogo width={36} height={36} simple={true} />
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
        
        <div className="flex items-center space-x-3">
          {/* Connection Status Indicator */}
          <div className="flex items-center space-x-2 bg-white/20 px-3 py-1 rounded-full">
            <div className={`w-2 h-2 rounded-full ${getStatusColor(pusherStatus.isConnected)} animate-pulse`}></div>
            <span className="text-white text-xs font-medium">
              {getConnectionStateText(pusherStatus.connectionState)}
            </span>
          </div>
          
          {/* Logs Button - Add this button */}
          <button
            onClick={() => setShowJenaLogs(true)}
            className="px-4 py-2 bg-frog-DEFAULT/20 text-white rounded-full hover:bg-frog-DEFAULT/30 focus:outline-none font-semibold transition-colors shadow-md flex items-center"
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
                d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Logs
          </button>
          
          {/* Knowledge Source Toggle */}
          <button
            onClick={toggleKnowledgeSource}
            className={`px-4 py-2 ${
              settings.knowledgeSource === 'wikidata' 
                ? 'bg-blue-500/50 hover:bg-blue-500/70' 
                : settings.knowledgeSource === 'curriculum'
                ? 'bg-purple-500/50 hover:bg-purple-500/70'
                : settings.knowledgeSource === 'legal'
                ? 'bg-red-500/50 hover:bg-red-500/70'
                : 'bg-green-500/50 hover:bg-green-500/70'
            } text-white rounded-full focus:outline-none font-semibold transition-colors shadow-md flex items-center`}
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
                d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            {settings.knowledgeSource === 'wikidata' ? 'Wikidata' : 
             settings.knowledgeSource === 'curriculum' ? 'Curriculum' :
             settings.knowledgeSource === 'legal' ? 'Legal' : 'GESIS'}
          </button>
          
          <button
            onClick={() => setShowSettings(true)}
            className="px-4 py-2 bg-frog-DEFAULT/20 text-white rounded-full hover:bg-frog-DEFAULT/30 focus:outline-none font-semibold transition-colors shadow-md flex items-center"
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
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Settings
          </button>
          
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
      </div>
      
      <Settings isOpen={showSettings} onClose={() => setShowSettings(false)} />
      <JenaLogsModal isOpen={showJenaLogs} onClose={() => setShowJenaLogs(false)} />
    </header>
  );
};

export default Header;