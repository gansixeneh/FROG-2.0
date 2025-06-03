import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { tomorrow } from "react-syntax-highlighter/dist/esm/styles/prism";

interface JenaLogsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const JenaLogsModal: React.FC<JenaLogsModalProps> = ({ isOpen, onClose }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  
  // SPARQL queries from the backend README
  const exampleQueries = [
    {
      title: "1. List All Runs with Timestamps",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?run ?startTime ?endTime ?duration ?totalEvents
WHERE {
  ?run rdf:type logex:ConversionMetadata ;
       logex:startTime ?startTime ;
       logex:endTime ?endTime ;
       logex:totalDuration ?duration ;
       logex:totalEvents ?totalEvents .
} 
ORDER BY DESC(?startTime)`
    },
    {
      title: "2. Find Runs with Specific Entities",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT DISTINCT ?run ?entityLabel ?startTime
WHERE {
  ?event log:hasEntity ?entity .
  ?event logex:belongsToRun ?run .
  ?entity rdfs:label ?entityLabel .
  ?run logex:startTime ?startTime .
  
  # Filter for specific entity (remove or change this filter as needed)
  FILTER(CONTAINS(LCASE(?entityLabel), "ma huateng"))
}
ORDER BY DESC(?startTime)`
    },
    {
      title: "3. Find SPARQL Queries Used in Runs",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT ?run ?queryText ?startTime
WHERE {
  ?event log:hasQuery ?query .
  ?event logex:belongsToRun ?run .
  ?query rdfs:label ?queryText .
  ?run logex:startTime ?startTime .
}
ORDER BY DESC(?startTime)`
    },
    {
      title: "4. Analyze Approach Distribution",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT ?approach (COUNT(?event) as ?count)
WHERE {
  ?event log:approach ?approach .
}
GROUP BY ?approach
ORDER BY DESC(?count)`
    },
    {
      title: "5. Calculate Average Duration by Component",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logid: <https://sepses.ifs.tuwien.ac.at/id/log#>

SELECT ?component (AVG(?duration) as ?avgDuration) (COUNT(?event) as ?count)
WHERE {
  ?event log:pname ?componentUri ;
         log:duration ?duration .
  BIND(STRAFTER(STR(?componentUri), "log#") as ?component)
}
GROUP BY ?component
ORDER BY DESC(?avgDuration)`
    },
    {
      title: "6. Find Most Common Entities",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>

SELECT ?entityLabel (COUNT(?entity) as ?count)
WHERE {
  ?event log:hasEntity ?entity .
  ?entity rdfs:label ?entityLabel .
}
GROUP BY ?entityLabel
ORDER BY DESC(?count)
LIMIT 20`
    },
    {
      title: "7. Find Most Common Wikidata Properties",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>

SELECT ?propertyId (COUNT(?property) as ?count)
WHERE {
  ?query log:referencesProperty ?property .
  ?property log:wikidataId ?propertyId .
}
GROUP BY ?propertyId
ORDER BY DESC(?count)
LIMIT 20`
    },
    {
      title: "8. Track Failed vs Successful SPARQL Queries",
      query: `PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT ?status (COUNT(?run) as ?count)
WHERE {
  {
    ?run logex:hasEventType ?eventType .
    ?eventType rdfs:label "all attempts failed" .
    BIND("failed" as ?status)
  }
  UNION
  {
    ?run logex:hasEventType ?eventType .
    ?eventType rdfs:label "successful query execution" .
    BIND("successful" as ?status)
  }
}
GROUP BY ?status`
    },
    {
      title: "9. Analyze Query Performance Over Time",
      query: `PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?date (AVG(?duration) as ?avgDuration) (COUNT(?run) as ?runCount)
WHERE {
  ?run logex:totalDuration ?duration ;
       logex:startTime ?startTime .
  BIND(SUBSTR(STR(?startTime), 1, 10) as ?date)
}
GROUP BY ?date
ORDER BY ?date`
    }
  ];

  // Copy query to clipboard
  const copyQuery = (query: string, index: number) => {
    navigator.clipboard.writeText(query);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-frog-dark flex items-center">
            <svg 
              width="24" 
              height="24" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              className="mr-2"
            >
              <path d="M12 2L2 7v10l10 5 10-5V7L12 2z" />
              <path d="M7 10l5 2 5-2M7 14l5 2 5-2" />
              <path d="M12 4v16" />
            </svg>
            FrOG Execution Logs - Apache Jena
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full"
          >
            <svg 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div className="space-y-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-gray-900 mb-2">About Apache Jena Logs</h3>
            <p className="text-sm text-gray-500 mb-3">
              FrOG integrates with Apache Jena Fuseki to store visualization logs in RDF format. This enables powerful 
              semantic querying of agent execution patterns, helping understand how the agent processes questions.
            </p>
            <div className="flex items-center justify-center mt-4">
              <a 
                href="https://generous-lark-duly.ngrok-free.app/#/dataset/visualization-logs/query" 
                target="_blank" 
                rel="noopener noreferrer"
                className="px-6 py-3 bg-frog-dark text-white rounded-md inline-flex items-center border-2 border-frog-dark shadow-lg font-medium"
              >
                <svg 
                  className="w-5 h-5 mr-2" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24" 
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Open Apache Jena SPARQL Endpoint
              </a>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Recommended SPARQL Queries</h3>
            <p className="text-sm text-gray-500 mb-4">
              Use these queries on the Fuseki SPARQL endpoint to analyze agent execution patterns. 
              Click the copy button to copy a query to your clipboard.
            </p>
            
            <div className="space-y-6">
              {exampleQueries.map((example, index) => (
                <div key={index} className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="font-medium text-frog-dark">{example.title}</h4>
                    <button
                      onClick={() => copyQuery(example.query, index)}
                      className="text-frog-dark hover:text-frog-medium transition-colors p-1"
                      title="Copy query"
                    >
                      {copiedIndex === index ? (
                        <svg
                          className="h-5 w-5 text-green-500"
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
                  </div>
                  <div className="relative group rounded overflow-hidden border border-frog-light">
                    <div className="bg-frog-dark/10 px-4 py-1 text-xs font-mono flex justify-between items-center border-b border-frog-light">
                      <span>SPARQL</span>
                    </div>
                    <SyntaxHighlighter
                      language="sparql"
                      style={tomorrow as any}
                      wrapLines={true}
                      showLineNumbers={true}
                    >
                      {example.query}
                    </SyntaxHighlighter>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-frog-DEFAULT text-white rounded-md hover:bg-frog-dark transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default JenaLogsModal;