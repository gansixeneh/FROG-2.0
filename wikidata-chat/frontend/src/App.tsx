// frontend/src/App.tsx
import React from 'react';
import { ChatProvider } from './context/ChatContext';
import Header from './components/Header';
import SideNav from './components/SideNav';
import ChatArea from './components/ChatArea';
import MessageInput from './components/MessageInput';

const App: React.FC = () => {
  return (
    <ChatProvider>
      <div className="flex h-screen bg-gray-50">
        <Header />
        <SideNav />
        <main className="flex-1 pt-16 pb-16 flex flex-col h-full overflow-hidden">
          <ChatArea />
          <MessageInput />
        </main>
      </div>
    </ChatProvider>
  );
};