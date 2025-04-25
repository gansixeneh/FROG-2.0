const { KGSchemaExtractor } = require('../kg_schema_extractor');
const { NL2SPARQLGenerator } = require('./nl2sparql_generator');

async function generateUniversityCourseDataset() {
  // Create a schema extractor
  const extractor = new KGSchemaExtractor();
  
  // Extract schema from your TTL file (this happens automatically)
  const schema = await extractor.extractFromFile('final_result.ttl', 'turtle');
  
  console.log(`Extracted ${schema.schemaInfo.types.length} types and ${schema.schemaInfo.properties.length} properties`);
  
  // Create generator with the automatically extracted schema
  const generator = new NL2SPARQLGenerator(schema);
  
  // Generate dataset
  const dataset = generator.generateDataset({
    size: 50,
    complexityDistribution: { basic: 0.5, intermediate: 0.3, advanced: 0.2 },
    includeVariations: true
  });
  
  // Export to files
  require('fs').writeFileSync('university_dataset.json', generator.exportJSON(dataset));
  require('fs').writeFileSync('university_dataset.csv', generator.exportCSV(dataset));
}

// Run the generator
generateUniversityCourseDataset();