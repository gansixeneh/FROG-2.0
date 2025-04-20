// frontend/src/App.tsx
import React from 'react';
import { ChatProvider } from './context/ChatContext';
import Header from './components/Header';
import SideNav from './components/SideNav';
import ChatArea from './components/ChatArea';
import MessageInput from './components/MessageInput';
import { useChat } from './context/ChatContext';

// Create a wrapper component to access the context
const AppContent: React.FC = () => {
  const { isNavOpen } = useChat();
  
  return (
    <div className="flex h-screen bg-gray-50">
      <Header />
      <SideNav />
      {/* Make the main content adapt to sidebar state */}
      <main 
        className={`flex-1 pt-16 pb-16 flex flex-col h-full overflow-hidden transition-all duration-300 ease-in-out ${
          isNavOpen ? 'ml-64' : 'ml-0'
        }`}
      >
        <ChatArea />
        <MessageInput />
      </main>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ChatProvider>
      <AppContent />
    </ChatProvider>
  );
};

export default App;