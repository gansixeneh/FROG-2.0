// frontend/src/App.tsx
import React from 'react';
import { ChatProvider } from './context/ChatContext';
import Header from './components/Header';
import SideNav from './components/SideNav';
import ChatArea from './components/ChatArea';
import MessageInput from './components/MessageInput';
import PusherDebug from './components/PusherDebug';
import { useChat } from './context/ChatContext';

// Create a wrapper component to access the context
const AppContent: React.FC = () => {
  const { isNavOpen } = useChat();
  
  // Decorative lily pads for ambiance
  const LilyPads = () => (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Large lily pad top right */}
      <div className="absolute top-20 right-10 w-28 h-28 rounded-full bg-frog-dark/5 transform rotate-12"></div>
      
      {/* Medium lily pad bottom left */}
      <div className="absolute bottom-20 left-10 w-20 h-20 rounded-full bg-frog-dark/5 transform -rotate-6"></div>
      
      {/* Small lily pads scattered around */}
      <div className="absolute top-1/3 left-1/4 w-12 h-12 rounded-full bg-frog-dark/5"></div>
      <div className="absolute top-2/3 right-1/3 w-10 h-10 rounded-full bg-frog-dark/5"></div>
      <div className="absolute top-1/2 right-1/4 w-16 h-16 rounded-full bg-frog-dark/5 transform rotate-45"></div>
    </div>
  );
  
  return (
    <div className="flex h-screen bg-frog-light overflow-hidden">
      <LilyPads />
      <Header />
      <SideNav />
      {/* Make the main content adapt to sidebar state */}
      <main 
        className={`flex-1 pt-16 pb-16 flex flex-col h-full overflow-hidden transition-all duration-300 ease-in-out relative ${
          isNavOpen ? 'ml-64' : 'ml-0'
        }`}
      >
        <ChatArea />
        <MessageInput />
      </main>
      {/* Add Pusher Debug component */}
      <PusherDebug />
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
