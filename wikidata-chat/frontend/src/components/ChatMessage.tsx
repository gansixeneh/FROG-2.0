// frontend/src/components/ChatMessage.tsx
import React, { useState, useEffect, useMemo } from "react";
import { Message } from "../types";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { tomorrow } from "react-syntax-highlighter/dist/esm/styles/prism";
import { formatSparqlQuery } from "../utils/sparqlFormatter";
import VisualizationFiles from "./VisualizationFiles";
import FrogLogo from "./FrogLogo"; // ADD THIS IMPORT
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

// Hook to create properly typed plugins
const useMarkdownPlugins = () => {
  return useMemo(() => ({
    remarkPlugins: [remarkGfm],
    rehypePlugins: [rehypeRaw as any],
  }), []);
};

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [showCopied, setShowCopied] = useState(false);
  const [processedContent, setProcessedContent] = useState(message.content);
  const { remarkPlugins, rehypePlugins } = useMarkdownPlugins();

  useEffect(() => {
    // Process the message content when the message changes
    setProcessedContent(processMessageContent(message.content));
  }, [message.content]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setShowCopied(true);
    setTimeout(() => setShowCopied(false), 2000);
  };

  const processMessageContent = (content: string) => {
    // Ensure there's a line break before any markdown heading (# headings)
    let processedContent = content.replace(/([^\n])(#{1,6}\s+)/g, "$1\n$2");

    // First, ensure there's a newline around the ```sparql tag
    processedContent = processedContent
      .replace(/(```sparql)/g, "\n$1")
      .replace(/```(?!sparql)/g, "```\n");

    // Format any SPARQL code blocks
    processedContent = processedContent.replace(
      /```sparql\s*([\s\S]*?)```/g,
      (match, code) => {
        try {
          // Use more spaces for better readability in the UI
          const formattedSparql = formatSparqlQuery(code, "default", 2);
          return "```sparql\n" + formattedSparql + "\n```";
        } catch (e) {
          console.error("Error formatting SPARQL:", e);
          return match; // Return original if formatting fails
        }
      }
    );

    // Look for URLs that aren't already in markdown link format: [text](url)
    const urlRegex = /(?<!\]\()https?:\/\/[^\s)>]+/g;
    processedContent = processedContent.replace(
      urlRegex,
      (url) => `[${url}](${url})`
    );

    return processedContent;
  };
  
  const FrogIcon = () => (
    <div className="w-8 h-8 rounded-full bg-frog-accent flex items-center justify-center mr-2 shadow-md">
      <FrogLogo width={24} height={24} simple={true} className="frog-logo-static" />
    </div>
  );
  
  // User icon
  const UserIcon = () => (
    <div className="w-8 h-8 rounded-full bg-frog-accent flex items-center justify-center ml-2 shadow-md">
      <svg 
        width="18" 
        height="18" 
        fill="none" 
        viewBox="0 0 24 24" 
        stroke="#166534" 
        strokeWidth="2"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" 
        />
      </svg>
    </div>
  );

  const renderUserMessage = () => (
    <div className="flex items-start justify-end">
      <div className="user-bubble px-4 py-3 bg-frog-accent text-frog-dark rounded-2xl rounded-tr-none shadow-md max-w-full">
        <ReactMarkdown
          className="prose max-w-none"
          remarkPlugins={remarkPlugins}
          rehypePlugins={rehypePlugins}
          remarkRehypeOptions={{ passThrough: ['link'] }}
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "");
              return !inline && match ? (
                <SyntaxHighlighter
                  language={match[1]}
                  style={tomorrow as any}
                  PreTag="div"
                  wrapLines={true}
                  showLineNumbers={match[1] === "sparql"}
                  {...props}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
            a: ({ node, children, href, ...props }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-frog-dark hover:text-frog-dark/70 underline break-all"
                {...props}
              >
                {children}
              </a>
            ),
          }}
        >
          {processedContent}
        </ReactMarkdown>
      </div>
      <UserIcon />
    </div>
  );

  const renderAssistantMessage = () => (
    <div className="flex items-start">
      <FrogIcon />
      <div className="assistant-bubble px-4 py-3 bg-white rounded-2xl rounded-tl-none shadow-md max-w-full relative">
        <button
          onClick={() => copyToClipboard(message.content)}
          className="absolute top-2 right-2 p-1 text-frog-dark/50 hover:text-frog-dark transition-colors"
          title="Copy to clipboard"
        >
          {showCopied ? (
            <svg
              className="h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ) : (
            <svg
              className="h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
              />
            </svg>
          )}
        </button>
        <ReactMarkdown
          className="prose max-w-none"
          remarkPlugins={remarkPlugins}
          rehypePlugins={rehypePlugins}
          remarkRehypeOptions={{ passThrough: ['link'] }}
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "");
              return !inline && match ? (
                <div className="relative group mt-4 rounded overflow-hidden border border-frog-light">
                  <div className="bg-frog-dark/10 px-4 py-1 text-xs font-mono flex justify-between items-center border-b border-frog-light">
                    <span>{match[1].toUpperCase()}</span>
                    <button
                      onClick={() => copyToClipboard(String(children))}
                      className="p-1 text-frog-dark/70 hover:text-frog-dark transition-colors"
                    >
                      <svg 
                        width="16" 
                        height="16" 
                        fill="none" 
                        viewBox="0 0 24 24" 
                        stroke="currentColor" 
                        strokeWidth="2"
                      >
                        <path d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                    </button>
                  </div>
                  <SyntaxHighlighter
                    language={match[1]}
                    style={tomorrow as any}
                    PreTag="div"
                    wrapLines={true}
                    showLineNumbers={match[1] === "sparql"}
                    {...props}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <code className="bg-frog-light/30 px-1 py-0.5 rounded text-frog-dark" {...props}>
                  {children}
                </code>
              );
            },
            a: ({ node, children, href, ...props }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-frog-dark hover:text-frog-dark/70 underline break-all"
                {...props}
              >
                {children}
              </a>
            ),
            h1: ({ node, children, ...props }) => (
              <h1 className="text-xl font-bold text-frog-dark mt-4 mb-2" {...props}>
                {children}
              </h1>
            ),
            h2: ({ node, children, ...props }) => (
              <h2 className="text-lg font-bold text-frog-dark mt-3 mb-2" {...props}>
                {children}
              </h2>
            ),
            h3: ({ node, children, ...props }) => (
              <h3 className="text-md font-bold text-frog-dark mt-3 mb-1" {...props}>
                {children}
              </h3>
            ),
          }}
        >
          {processedContent}
        </ReactMarkdown>
        
        {/* Add visualization files component */}
        <VisualizationFiles message={message} />
      </div>
    </div>
  );

  return (
    <div className="mb-6">
      {message.role === "user" && renderUserMessage()}
      {message.role === "assistant" && renderAssistantMessage()}
    </div>
  );
};

export default ChatMessage;