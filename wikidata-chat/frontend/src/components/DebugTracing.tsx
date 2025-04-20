// frontend/src/components/DebugTracing.tsx
import React from 'react';
import { DebugOutput } from '../types';

interface DebugTracingProps {
  debugItems: DebugOutput[];
}

const DebugTracing: React.FC<DebugTracingProps> = ({ debugItems }) => {
  if (!debugItems || debugItems.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm max-h-64 overflow-y-auto">
      <div className="mb-2">
        <h4 className="text-white font-bold">Agent Reasoning</h4>
      </div>
      <pre className="whitespace-pre-wrap">
        {debugItems.map((debug, index) => (
          <div key={index} className="mb-2">
            {debug.content}
          </div>
        ))}
      </pre>
    </div>
  );
};

export default DebugTracing;