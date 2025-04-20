// frontend/src/components/ChatMessage.tsx
import React, { useState, useEffect } from "react";
import { Message } from "../types";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { tomorrow } from "react-syntax-highlighter/dist/esm/styles/prism";
import { formatSparqlQuery } from "../utils/sparqlFormatter";

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const [showCopied, setShowCopied] = useState(false);
  const [processedContent, setProcessedContent] = useState(message.content);

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

  const renderUserMessage = () => (
    <div className="px-4 py-3 bg-blue-50 rounded-lg">
      <ReactMarkdown
        className="prose max-w-none"
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
              className="text-blue-600 hover:text-blue-800 underline break-all"
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
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "");
              return !inline && match ? (
                <div className="relative group">
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
              );
            },
            a: ({ node, children, href, ...props }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline break-all"
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
    </div>
  );

  return (
    <div
      className={`mb-4 ${
        message.role === "user"
          ? "text-right"
          : "text-left" 
      }`}
    >
      <div
        className={`inline-block ${
          message.role === "user"
            ? "ml-auto max-w-[65%]"
            : "mr-auto max-w-[65%]"
        }`}
      >
        {message.role === "user" && renderUserMessage()}
        {message.role === "assistant" && renderAssistantMessage()}
      </div>
    </div>
  );
};

export default ChatMessage;