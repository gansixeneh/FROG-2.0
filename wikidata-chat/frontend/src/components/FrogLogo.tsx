// frontend/src/components/FrogLogo.tsx
import React from 'react';

interface FrogLogoProps {
  width?: number;
  height?: number;
  className?: string;
}

const FrogLogo: React.FC<FrogLogoProps> = ({ 
  width = 200, 
  height = 200,
  className = "frog-logo"
}) => {
  return (
    <svg 
      width={width} 
      height={height} 
      viewBox="0 0 400 400" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Main frog head - green */}
      <circle cx="200" cy="170" r="120" fill="#4ade80" stroke="#166534" strokeWidth="8" />
      
      {/* Eyes */}
      <circle cx="150" cy="130" r="30" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="150" cy="130" r="15" fill="#166534" />
      <circle cx="250" cy="130" r="30" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="250" cy="130" r="15" fill="#166534" />
      
      {/* Cheeks with knowledge graph icons */}
      <circle cx="120" cy="180" r="25" fill="#166534" opacity="0.7" />
      <circle cx="280" cy="180" r="25" fill="#166534" opacity="0.7" />
      
      {/* Network nodes in cheeks */}
      <circle cx="120" cy="180" r="20" fill="#a6e9a6" />
      <circle cx="280" cy="180" r="20" fill="#a6e9a6" />
      
      {/* Smile */}
      <path d="M150,220 Q200,245 250,220" stroke="#166534" strokeWidth="8" fill="none" />
      
      {/* Decorative nodes on the knowledge graph in the cheeks */}
      <circle cx="110" cy="170" r="3" fill="#fef08a" />
      <circle cx="125" cy="170" r="3" fill="#fef08a" />
      <circle cx="130" cy="185" r="3" fill="#fef08a" />
      <circle cx="115" cy="190" r="3" fill="#fef08a" />
      <circle cx="105" cy="185" r="3" fill="#fef08a" />
      
      <circle cx="270" cy="170" r="3" fill="#fef08a" />
      <circle cx="285" cy="170" r="3" fill="#fef08a" />
      <circle cx="290" cy="185" r="3" fill="#fef08a" />
      <circle cx="275" cy="190" r="3" fill="#fef08a" />
      <circle cx="265" cy="185" r="3" fill="#fef08a" />
      
      {/* "Network" lines in cheeks */}
      <line x1="110" y1="170" x2="125" y2="170" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="125" y1="170" x2="130" y2="185" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="130" y1="185" x2="115" y2="190" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="115" y1="190" x2="105" y2="185" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="105" y1="185" x2="110" y2="170" stroke="#fef08a" strokeWidth="1.5" />
      
      <line x1="270" y1="170" x2="285" y2="170" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="285" y1="170" x2="290" y2="185" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="290" y1="185" x2="275" y2="190" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="275" y1="190" x2="265" y2="185" stroke="#fef08a" strokeWidth="1.5" />
      <line x1="265" y1="185" x2="270" y2="170" stroke="#fef08a" strokeWidth="1.5" />
      
      {/* Frog body/shirt */}
      <rect x="140" y="290" width="120" height="100" fill="#fef08a" rx="20" ry="20" stroke="#166534" strokeWidth="6" />
      
      {/* Arms */}
      <circle cx="100" cy="240" r="15" fill="#4ade80" stroke="#166534" strokeWidth="4" />
      <circle cx="300" cy="240" r="15" fill="#4ade80" stroke="#166534" strokeWidth="4" />
      <line x1="115" y1="240" x2="140" y2="250" stroke="#4ade80" strokeWidth="30" strokeLinecap="round" />
      <line x1="285" y1="240" x2="260" y2="250" stroke="#4ade80" strokeWidth="30" strokeLinecap="round" />
      <line x1="115" y1="240" x2="140" y2="250" stroke="#166534" strokeWidth="4" strokeLinecap="round" />
      <line x1="285" y1="240" x2="260" y2="250" stroke="#166534" strokeWidth="4" strokeLinecap="round" />
      
      {/* Legs */}
      <circle cx="140" cy="350" r="15" fill="#4ade80" stroke="#166534" strokeWidth="4" />
      <circle cx="260" cy="350" r="15" fill="#4ade80" stroke="#166534" strokeWidth="4" />
      
      {/* Wikidata barcode in the middle of the body */}
      <rect x="175" y="310" width="50" height="60" fill="white" rx="4" ry="4" stroke="#166534" strokeWidth="2" />
      <text x="200" y="380" textAnchor="middle" fill="#166534" fontFamily="monospace" fontSize="10" fontWeight="bold">WIKIDATA</text>
      
      {/* Barcode lines */}
      <rect x="180" y="320" width="2" height="40" fill="#166534" />
      <rect x="185" y="320" width="5" height="40" fill="#166534" />
      <rect x="192" y="320" width="1" height="40" fill="#166534" />
      <rect x="195" y="320" width="3" height="40" fill="#166534" />
      <rect x="200" y="320" width="4" height="40" fill="#166534" />
      <rect x="206" y="320" width="2" height="40" fill="#166534" />
      <rect x="210" y="320" width="3" height="40" fill="#166534" />
      <rect x="215" y="320" width="5" height="40" fill="#166534" />
      <rect x="222" y="320" width="1" height="40" fill="#166534" />
      
      {/* Knowledge graph connections */}
      <circle cx="60" cy="100" r="15" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="60" cy="100" r="5" fill="#166534" />
      <line x1="60" y1="100" x2="120" y2="170" stroke="#166534" strokeWidth="3" />
      
      <circle cx="100" cy="60" r="15" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="100" cy="60" r="5" fill="#166534" />
      <line x1="100" y1="60" x2="150" y2="130" stroke="#166534" strokeWidth="3" />
      
      <circle cx="300" cy="60" r="15" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="300" cy="60" r="5" fill="#166534" />
      <line x1="300" y1="60" x2="250" y2="130" stroke="#166534" strokeWidth="3" />
      
      <circle cx="340" cy="100" r="15" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="340" cy="100" r="5" fill="#166534" />
      <line x1="340" y1="100" x2="280" y2="170" stroke="#166534" strokeWidth="3" />
      
      <circle cx="340" cy="180" r="15" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="340" cy="180" r="5" fill="#166534" />
      <line x1="340" y1="180" x2="280" y2="190" stroke="#166534" strokeWidth="3" />
      
      <circle cx="60" cy="180" r="15" fill="white" stroke="#166534" strokeWidth="4" />
      <circle cx="60" cy="180" r="5" fill="#166534" />
      <line x1="60" y1="180" x2="110" y2="190" stroke="#166534" strokeWidth="3" />
    </svg>
  );
};

export default FrogLogo;