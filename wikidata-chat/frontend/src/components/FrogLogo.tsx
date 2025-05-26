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
    <img 
      src="/assets/frog-logo.svg"
      alt="FrOG Logo"
      width={width}
      height={height}
      className={className}
      style={{ 
        width: `${width}px`, 
        height: `${height}px` 
      }}
    />
  );
};

export default FrogLogo;