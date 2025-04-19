// frontend/src/components/ChatMessage.tsx
import React, { useState } from 'react';
import { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [showCopied, setShowCopied] = useState(false);
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setShowCopied(true);
    setTimeout(() => setShowCopied(false), 2000);
  };
  
  const renderUserMessage = () => (
    <div className="px-4 py-3 bg-blue-50 rounded-lg">
      <ReactMarkdown
        className="prose max-w-none"
        components={{
          code: ({node, inline, className, children, ...props}) => {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter
                language={match[1]}
                style={tomorrow as any}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            )
          }
        }}
      >
        {message.content}
      </ReactMarkdown>
    </div>
  );
  
  const renderAssistantMessage = () => (
    <div className="px-4 py-3 bg-white rounded-lg shadow">
      <div className="relative">
        <button
          onClick={() => copyToClipboard(message.content)}
          className="absolute top-0 right-0 p-2 text-gray-400 hover:text-gray-600"
          title="Copy to clipboard"
        >
          {showCopied ? (
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
          )}
        </button>
        <ReactMarkdown
          className="prose max-w-none"
          components={{
            code: ({node, inline, className, children, ...props}) => {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <div className="relative group">
                  <SyntaxHighlighter
                    language={match[1]}
                    style={tomorrow as any}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                  <button
                    onClick={() => copyToClipboard(String(children))}
                    className="absolute top-2 right-2 p-1 bg-gray-700 rounded text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    Copy
                  </button>
                </div>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              )
            }
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    </div>
  );
  
  const renderSystemMessage = () => (
    <div className="px-4 py-2 bg-gray-100 rounded text-gray-700 text-sm">
      <div className="italic">{message.content}</div>
    </div>
  );

  return (
    <div className={`mb-4 ${
      message.role === 'user' 
        ? 'text-right' 
        : message.role === 'assistant' 
          ? 'text-left' 
          : 'mx-auto text-center'
    }`}>
      <div className={`inline-block ${
        message.role === 'user' 
          ? 'ml-auto max-w-[80%]' 
          : message.role === 'assistant' 
            ? 'mr-auto max-w-[80%]' 
            : 'mx-auto max-w-[90%]'
      }`}>
        {message.role === 'user' && renderUserMessage()}
        {message.role === 'assistant' && renderAssistantMessage()}
        {message.role === 'system' && renderSystemMessage()}
      </div>
    </div>
  );
};

export default ChatMessage;