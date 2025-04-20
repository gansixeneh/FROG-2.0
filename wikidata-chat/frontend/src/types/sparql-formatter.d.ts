declare module 'sparql-formatter' {
    export const spfmt: {
      format: (
        query: string, 
        formattingMode?: 'default' | 'compact' | 'turtle' | 'jsonld', 
        indentDepth?: number
      ) => string;
    };
  }