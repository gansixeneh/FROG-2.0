import React from 'react';
import { useChat } from '../context/ChatContext';
import '../styles/VisualizationFiles.css';

const VisualizationFiles = ({ messageId }) => {
  const { visualizationFiles, downloadVisualizationFile } = useChat();

  if (!visualizationFiles) return null;

  // Check if any files are available
  const hasFiles = Object.values(visualizationFiles).some(val => val);
  if (!hasFiles) return null;

  const handleDownload = (fileType) => {
    downloadVisualizationFile(fileType);
  };

  return (
    <div className="visualization-files">
      <h4>Visualization Files</h4>
      <div className="visualization-buttons">
        {visualizationFiles.json && (
          <button 
            className="visualization-button json-file"
            onClick={() => handleDownload('json')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M4 20h16V8H4v12zM14 2v4h4L14 2zm-2 0H6C4.9 2 4 2.9 4 4v2h8V2z" fill="#F57C00"/>
              <path d="M8 14h2v4H8v-4z" fill="#F57C00"/>
              <path d="M12 14h2v4h-2v-4z" fill="#F57C00"/>
              <path d="M16 14h2v4h-2v-4z" fill="#F57C00"/>
            </svg>
            JSON
          </button>
        )}
        
        {visualizationFiles.mermaid && (
          <button 
            className="visualization-button mermaid-file"
            onClick={() => handleDownload('mermaid')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 3h18v18H3V3z" fill="#E3F2FD"/>
              <path d="M12 17.5l5.5-5.5H14v-5h-4v5H6.5L12 17.5z" fill="#2196F3"/>
            </svg>
            Mermaid Diagram
          </button>
        )}
        
        {visualizationFiles.ttl && (
          <button 
            className="visualization-button ttl-file"
            onClick={() => handleDownload('ttl')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" fill="#4CAF50" fillOpacity="0.5"/>
              <path d="M7 10l5 2 5-2M7 14l5 2 5-2" stroke="#4CAF50" strokeWidth="1.5"/>
              <path d="M12 4v16" stroke="#4CAF50" strokeWidth="1.5"/>
            </svg>
            TTL Graph
          </button>
        )}
      </div>
    </div>
  );
};

export default VisualizationFiles;
