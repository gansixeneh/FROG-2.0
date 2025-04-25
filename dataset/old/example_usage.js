/**
 * Example usage of the NL2SPARQL Generator
 * 
 * This example demonstrates how to use the generator with:
 * 1. DBpedia knowledge graph schema
 * 2. Wikidata knowledge graph schema
 * 3. Custom domain-specific knowledge graph
 */

// Import the required modules
const { NL2SPARQLGenerator } = require('./nl2sparql_generator');
const { KGSchemaExtractor } = require('../kg_schema_extractor');

// Example 1: Using the generator with DBpedia
function generateDBpediaDataset() {
  console.log("Generating DBpedia question-SPARQL dataset...");
  
  const dbpediaConfig = {
    prefixes: {
      'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
      'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
      'owl': 'http://www.w3.org/2002/07/owl#',
      'dbo': 'http://dbpedia.org/ontology/',
      'dbr': 'http://dbpedia.org/resource/',
      'dbp': 'http://dbpedia.org/property/',
      'xsd': 'http://www.w3.org/2001/XMLSchema#'
    },
    entityExamples: [
      { value: 'dbr:Berlin', label: 'Berlin', uri: 'http://dbpedia.org/resource/Berlin' },
      { value: 'dbr:Paris', label: 'Paris', uri: 'http://dbpedia.org/resource/Paris' },
      { value: 'dbr:Germany', label: 'Germany', uri: 'http://dbpedia.org/resource/Germany' },
      { value: 'dbr:France', label: 'France', uri: 'http://dbpedia.org/resource/France' },
      { value: 'dbr:Leonardo_da_Vinci', label: 'Leonardo da Vinci', uri: 'http://dbpedia.org/resource/Leonardo_da_Vinci' },
      { value: 'dbr:Mona_Lisa', label: 'Mona Lisa', uri: 'http://dbpedia.org/resource/Mona_Lisa' }
    ],
    schemaInfo: {
      properties: [
        { value: 'dbo:capital', label: 'capital', uri: 'http://dbpedia.org/ontology/capital' },
        { value: 'dbo:country', label: 'country', uri: 'http://dbpedia.org/ontology/country' },
        { value: 'dbo:populationTotal', label: 'population', uri: 'http://dbpedia.org/ontology/populationTotal' },
        { value: 'dbo:author', label: 'author', uri: 'http://dbpedia.org/ontology/author' },
        { value: 'dbo:artist', label: 'artist', uri: 'http://dbpedia.org/ontology/artist' }
      ],
      types: [
        { value: 'dbo:City', label: 'City', uri: 'http://dbpedia.org/ontology/City' },
        { value: 'dbo:Country', label: 'Country', uri: 'http://dbpedia.org/ontology/Country' },
        { value: 'dbo:Person', label: 'Person', uri: 'http://dbpedia.org/ontology/Person' }
      ],
      numericProperties: [
        { value: 'dbo:populationTotal', label: 'population', uri: 'http://dbpedia.org/ontology/populationTotal' }
      ],
      dateProperties: [
        { value: 'dbo:foundingDate', label: 'founding date', uri: 'http://dbpedia.org/ontology/foundingDate' },
        { value: 'dbo:birthDate', label: 'birth date', uri: 'http://dbpedia.org/ontology/birthDate' }
      ]
    }
  };

  const generator = new NL2SPARQLGenerator(dbpediaConfig);
  
  // Generate a small dataset
  const dataset = generator.generateDataset({
    size: 100,
    complexityDistribution: { basic: 0.5, intermediate: 0.3, advanced: 0.15, expert: 0.05 },
    includeVariations: true,
    variationsPerQuestion: 2
  });
  
  console.log(`Generated ${dataset.length} question-SPARQL pairs`);
  
  // Export to different formats
  const jsonOutput = generator.exportJSON(dataset);
  const csvOutput = generator.exportCSV(dataset);
  
  // Write to files
  const fs = require('fs');
  fs.writeFileSync('dbpedia_dataset.json', jsonOutput);
  fs.writeFileSync('dbpedia_dataset.csv', csvOutput);
  
  console.log("Dataset exported to JSON and CSV files");
  
  return dataset;
}

// Example 2: Extract schema from SPARQL endpoint and generate dataset
async function extractAndGenerate() {
  try {
    console.log("Extracting schema from DBpedia endpoint...");
    
    const extractor = new KGSchemaExtractor();
    const schema = await extractor.extractFromEndpoint('https://dbpedia.org/sparql');
    
    console.log(`Extracted schema with ${schema.schemaInfo.types.length} types and ${schema.schemaInfo.properties.length} properties`);
    
    // Generate dataset using extracted schema
    const generator = new NL2SPARQLGenerator({
      prefixes: schema.prefixes,
      entityExamples: schema.entityExamples,
      schemaInfo: schema.schemaInfo
    });
    
    const dataset = generator.generateDataset({
      size: 100,
      complexityDistribution: { basic: 0.6, intermediate: 0.3, advanced: 0.1 }
    });
    
    console.log(`Generated ${dataset.length} question-SPARQL pairs from extracted schema`);
    
    // Write to file
    require('fs').writeFileSync('extracted_dataset.json', generator.exportJSON(dataset));
    
    return dataset;
  } catch (error) {
    console.error("Error extracting schema and generating dataset:", error);
    throw error;
  }
}

// Example 3: Generate dataset with custom domain-specific templates
function generateBiomedicalDataset() {
  console.log("Generating biomedical question-SPARQL dataset...");
  
  // Configuration for a biomedical knowledge graph
  const biomedicalConfig = {
    prefixes: {
      'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
      'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
      'owl': 'http://www.w3.org/2002/07/owl#',
      'xsd': 'http://www.w3.org/2001/XMLSchema#',
      'bio': 'http://example.org/biomedical/',
      'disease': 'http://example.org/biomedical/disease/',
      'drug': 'http://example.org/biomedical/drug/',
      'gene': 'http://example.org/biomedical/gene/'
    },
    entityExamples: [
      { value: 'disease:D001249', label: 'Alzheimer\'s Disease', uri: 'http://example.org/biomedical/disease/D001249' },
      { value: 'disease:D003924', label: 'Diabetes Mellitus', uri: 'http://example.org/biomedical/disease/D003924' },
      { value: 'drug:DB00619', label: 'Aspirin', uri: 'http://example.org/biomedical/drug/DB00619' },
      { value: 'drug:DB00945', label: 'Insulin', uri: 'http://example.org/biomedical/drug/DB00945' },
      { value: 'gene:G001', label: 'BRCA1', uri: 'http://example.org/biomedical/gene/G001' },
      { value: 'gene:G002', label: 'TP53', uri: 'http://example.org/biomedical/gene/G002' }
    ],
    schemaInfo: {
      properties: [
        { value: 'bio:treats', label: 'treats', uri: 'http://example.org/biomedical/treats' },
        { value: 'bio:causedBy', label: 'caused by', uri: 'http://example.org/biomedical/causedBy' },
        { value: 'bio:associatedWith', label: 'associated with', uri: 'http://example.org/biomedical/associatedWith' },
        { value: 'bio:hasSymptom', label: 'has symptom', uri: 'http://example.org/biomedical/hasSymptom' }
      ],
      types: [
        { value: 'bio:Disease', label: 'Disease', uri: 'http://example.org/biomedical/Disease' },
        { value: 'bio:Drug', label: 'Drug', uri: 'http://example.org/biomedical/Drug' },
        { value: 'bio:Gene', label: 'Gene', uri: 'http://example.org/biomedical/Gene' },
        { value: 'bio:Protein', label: 'Protein', uri: 'http://example.org/biomedical/Protein' }
      ],
      numericProperties: [
        { value: 'bio:prevalence', label: 'prevalence', uri: 'http://example.org/biomedical/prevalence' }
      ],
      dateProperties: [
        { value: 'bio:discoveryDate', label: 'discovery date', uri: 'http://example.org/biomedical/discoveryDate' }
      ]
    },
    // Add domain-specific custom templates
    customTemplates: [
      {
        id: "bio-drug-disease",
        category: "biomedical",
        questionTemplate: "Which drugs are used to treat {entity}?",
        sparqlTemplate: `
          SELECT DISTINCT ?drug WHERE {
            ?drug a bio:Drug .
            ?drug bio:treats {entity} .
          }
        `,
        complexity: "basic"
      },
      {
        id: "bio-gene-disease",
        category: "biomedical",
        questionTemplate: "Which genes are associated with {entity}?",
        sparqlTemplate: `
          SELECT DISTINCT ?gene WHERE {
            ?gene a bio:Gene .
            ?gene bio:associatedWith {entity} .
          }
        `,
        complexity: "basic"
      }
    ]
  };

  const generator = new NL2SPARQLGenerator(biomedicalConfig);
  
  // Generate dataset
  const dataset = generator.generateDataset({
    size: 100,
    complexityDistribution: { basic: 0.7, intermediate: 0.3 },
    includeVariations: true
  });
  
  console.log(`Generated ${dataset.length} biomedical question-SPARQL pairs`);
  
  return dataset;
}

// Main function to run all examples
async function main() {
  try {
    // Generate dataset with predefined schema
    const dbpediaDataset = generateDBpediaDataset();
    
    // Generate dataset with domain-specific templates
    const biomedicalDataset = generateBiomedicalDataset();
    
    // Extract schema and generate dataset (commented out as it requires internet connection)
    // const extractedDataset = await extractAndGenerate();
    
    console.log("All examples completed successfully!");
  } catch (error) {
    console.error("Error in examples:", error);
  }
}

// Run the examples
main();