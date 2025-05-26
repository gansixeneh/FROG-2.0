// frontend/src/components/PusherDebug.tsx
import React, { useState, useEffect } from 'react';
import { pusherService } from '../services/pusherService';
import { useChat } from '../context/ChatContext';

const PusherDebug: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [isVisible, setIsVisible] = useState(false);
  const { pusherStatus } = useChat();

  useEffect(() => {
    // Override console.log temporarily to capture Pusher logs
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    const captureLog = (level: string, ...args: any[]) => {
      const message = args.join(' ');
      if (message.includes('Pusher') || message.includes('📡') || message.includes('🐛') || 
          message.includes('💬') || message.includes('🔧') || message.includes('📨') ||
          message.includes('✅') || message.includes('❌') || message.includes('🔄') ||
          message.includes('⏳') || message.includes('🎯') || message.includes('📝')) {
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [...prev.slice(-19), `[${timestamp}] ${level}: ${message}`]);
      }
    };

    console.log = (...args) => {
      originalLog(...args);
      captureLog('LOG', ...args);
    };

    console.error = (...args) => {
      originalError(...args);
      captureLog('ERROR', ...args);
    };

    console.warn = (...args) => {
      originalWarn(...args);
      captureLog('WARN', ...args);
    };

    return () => {
      console.log = originalLog;
      console.error = originalError;
      console.warn = originalWarn;
    };
  }, []);

  const getStatusColor = (isConnected: boolean) => {
    return isConnected ? 'bg-green-500' : 'bg-red-500';
  };

  const getConnectionStateText = (state: string) => {
    switch (state) {
      case 'connected': return '✅ Connected';
      case 'connecting': return '🔄 Connecting';
      case 'disconnected': return '❌ Disconnected';
      case 'unavailable': return '⚠️ Unavailable';
      default: return `❓ ${state}`;
    }
  };

  if (!isVisible) {
    return (
      <div className="fixed bottom-20 right-4 z-50">
        <div className="flex flex-col items-end space-y-2">
          {/* Status indicator */}
          <div className="bg-white border-2 border-frog-dark rounded-lg shadow-lg p-2 text-xs">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${getStatusColor(pusherStatus.isConnected)}`}></div>
              <span className="font-mono">{getConnectionStateText(pusherStatus.connectionState)}</span>
            </div>
            {pusherStatus.currentChannel && (
              <div className="text-gray-600 mt-1">
                📡 {pusherStatus.currentChannel}
              </div>
            )}
          </div>
          
          {/* Debug button */}
          <button
            onClick={() => setIsVisible(true)}
            className="bg-frog-dark text-white px-3 py-2 rounded-lg text-sm hover:bg-frog-dark/80"
          >
            🐛 Debug
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-20 right-4 bg-white border-2 border-frog-dark rounded-lg shadow-lg p-4 max-w-md w-80 z-50">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-bold text-frog-dark">Pusher Debug</h3>
        <button
          onClick={() => setIsVisible(false)}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>
      
      {/* Connection Status */}
      <div className="mb-3 p-2 bg-gray-50 rounded">
        <div className="flex items-center space-x-2 mb-1">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(pusherStatus.isConnected)}`}></div>
          <span className="font-mono text-sm">{getConnectionStateText(pusherStatus.connectionState)}</span>
        </div>
        {pusherStatus.currentChannel && (
          <div className="text-xs text-gray-600">
            Channel: {pusherStatus.currentChannel}
          </div>
        )}
      </div>
      
      <div className="h-40 overflow-y-auto bg-gray-100 p-2 rounded text-xs font-mono">
        {logs.length === 0 ? (
          <div className="text-gray-500">No logs yet...</div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="mb-1 break-words">
              {log}
            </div>
          ))
        )}
      </div>
      
      <div className="flex space-x-2 mt-2">
        <button
          onClick={() => setLogs([])}
          className="px-2 py-1 bg-frog-light text-frog-dark rounded text-xs"
        >
          Clear Logs
        </button>
        <button
          onClick={() => {
            console.log('🧪 Manual test message');
            console.log('Pusher Status:', pusherService.getConnectionStatus());
          }}
          className="px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs"
        >
          Test Log
        </button>
      </div>
    </div>
  );
};

export default PusherDebug;
