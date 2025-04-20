// frontend/src/components/SystemMessageGroup.tsx
import React, { useState } from "react";
import { Message } from "../types";

interface SystemMessageGroupProps {
  messages: Message[];
}

const SystemMessageGroup: React.FC<SystemMessageGroupProps> = ({ messages }) => {
  const [isVisible, setIsVisible] = useState(false);

  // Combine all system message contents
  const combinedContent = messages.map(msg => msg.content).join("\n\n");
  
  // Create a unique identifier for this group based on the first message ID
  const groupId = messages.length > 0 ? messages[0].id : "group-fallback";

  return (
    <div className="mx-auto max-w-[90%] w-full mb-4">
      <button
        onClick={() => setIsVisible(!isVisible)}
        className="w-full text-sm font-medium py-2 px-3 bg-gray-700 text-gray-300 hover:bg-gray-600 rounded-md flex items-center justify-center"
      >
        {isVisible ? "Hide Agent Tracing" : "Show Agent Tracing"}
        <svg
          className={`ml-2 h-4 w-4 transition-transform ${isVisible ? "rotate-180" : ""}`}
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
      
      {isVisible && (
        <div 
          className="bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm mt-2 max-h-[400px] overflow-y-auto"
        >
          <pre className="whitespace-pre-wrap">{combinedContent}</pre>
        </div>
      )}
    </div>
  );
};

export default SystemMessageGroup;