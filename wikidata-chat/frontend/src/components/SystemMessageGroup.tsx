// frontend/src/components/SystemMessageGroup.tsx
import React, { useState, useRef, useEffect } from "react";
import { Message } from "../types";

interface SystemMessageGroupProps {
  messages: Message[];
}

const SystemMessageGroup: React.FC<SystemMessageGroupProps> = ({ messages }) => {
  const [isVisible, setIsVisible] = useState(true); // Auto-expand tracing by default
  const [height, setHeight] = useState<number | undefined>(undefined);
  const contentRef = useRef<HTMLDivElement>(null);

  // Combine all system message contents
  const combinedContent = messages.map(msg => msg.content).join("\n\n");
  
  // Create a unique identifier for this group based on the first message ID
  const groupId = messages.length > 0 ? messages[0].id : "group-fallback";

  // Calculate the content height when it becomes visible or when messages change
  useEffect(() => {
    if (isVisible && contentRef.current) {
      // Set max height to the actual content height (capped at 400px)
      const contentHeight = contentRef.current.scrollHeight;
      setHeight(Math.min(contentHeight, 400));
    } else {
      setHeight(0);
    }
  }, [isVisible, messages]); // Add messages as a dependency to recalculate when they change

  // Auto-scroll to the bottom of the trace content when new messages arrive
  useEffect(() => {
    if (isVisible && contentRef.current) {
      const container = contentRef.current.querySelector('.agent-trace-content');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [messages, isVisible]);

  return (
    <div className="mx-auto max-w-[680px] w-full mb-6">
      <button
        onClick={() => setIsVisible(!isVisible)}
        className="w-full text-sm font-medium py-2 px-3 bg-frog-dark text-white hover:bg-frog-dark/80 rounded-t-md flex items-center justify-center transition-colors duration-200"
      >
        <div className="flex items-center">
          <svg 
            width="20" 
            height="20" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            className="mr-2"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth="2" 
              d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
            />
          </svg>
          {isVisible ? "Hide FrOG Reasoning" : "Show FrOG Reasoning"}
        </div>
        <svg
          className={`ml-2 h-4 w-4 transition-transform duration-300 ${isVisible ? "rotate-180" : ""}`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      
      <div 
        ref={contentRef}
        className={`bg-gradient-to-r from-frog-dark via-frog-dark/90 to-frog-dark 
                  text-frog-accent p-4 rounded-b-md font-mono text-sm 
                  overflow-hidden transition-all duration-300 ease-in-out
                  border-t-0 border-2 border-frog-dark shadow-lg`}
        style={{ 
          maxHeight: height !== undefined ? `${height}px` : undefined,
          opacity: isVisible ? 1 : 0
        }}
      >
        {/* Decorative elements for frog theme */}
        <div className="absolute top-2 right-2 flex space-x-1">
          <div className="w-2 h-2 bg-frog-light rounded-full opacity-70"></div>
          <div className="w-2 h-2 bg-frog-accent rounded-full opacity-70"></div>
        </div>
        
        {/* Use overflow-y-auto to ensure we get scrollbars when needed */}
        <div className="max-h-[400px] overflow-y-auto pr-2 agent-trace-content">
          <pre className="whitespace-pre-wrap">{combinedContent}</pre>
        </div>
        
        {/* Lily pad decoration */}
        <div className="absolute bottom-1 left-6 w-20 h-2 bg-frog-accent/30 rounded-full"></div>
      </div>
    </div>
  );
};

export default SystemMessageGroup;