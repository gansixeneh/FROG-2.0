/**
 * NL2SPARQL - Natural Language to SPARQL Dataset Generator
 * 
 * This tool creates pairs of natural language questions and corresponding SPARQL queries
 * for any knowledge graph by using templates and entity instantiation.
 * 
 * Usage example:
 * 
 * // Configure with KG schema information
 * const config = {
 *   prefixes: {
 *     'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
 *     'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
 *     'dbo': 'http://dbpedia.org/ontology/',
 *     'dbr': 'http://dbpedia.org/resource/',
 *     'xsd': 'http://www.w3.org/2001/XMLSchema#'
 *   },
 *   entityExamples: [
 *     { value: 'dbr:Berlin', label: 'Berlin', uri: 'http://dbpedia.org/resource/Berlin' },
 *     { value: 'dbr:Paris', label: 'Paris', uri: 'http://dbpedia.org/resource/Paris' },
 *     { value: 'dbr:Leonardo_da_Vinci', label: 'Leonardo da Vinci', uri: 'http://dbpedia.org/resource/Leonardo_da_Vinci' }
 *   ],
 *   schemaInfo: {
 *     properties: [
 *       { value: 'dbo:capital', label: 'capital', uri: 'http://dbpedia.org/ontology/capital' },
 *       { value: 'dbo:populationTotal', label: 'population', uri: 'http://dbpedia.org/ontology/populationTotal' }
 *     ],
 *     types: [
 *       { value: 'dbo:City', label: 'City', uri: 'http://dbpedia.org/ontology/City' },
 *       { value: 'dbo:Country', label: 'Country', uri: 'http://dbpedia.org/ontology/Country' }
 *     ],
 *     numericProperties: [
 *       { value: 'dbo:populationTotal', label: 'population', uri: 'http://dbpedia.org/ontology/populationTotal' }
 *     ],
 *     dateProperties: [
 *       { value: 'dbo:foundingDate', label: 'founding date', uri: 'http://dbpedia.org/ontology/foundingDate' }
 *     ]
 *   }
 * };
 * 
 * const generator = new NL2SPARQLGenerator(config);
 * 
 * // Generate a dataset with 100 question-query pairs
 * const dataset = generator.generateDataset({
 *   size: 100,
 *   complexityDistribution: { basic: 0.5, intermediate: 0.3, advanced: 0.15, expert: 0.05 },
 *   includeVariations: true,
 *   variationsPerQuestion: 2
 * });
 * 
 * // Export to JSON
 * const jsonOutput = generator.exportJSON(dataset);
 * 
 * // Export to CSV
 * const csvOutput = generator.exportCSV(dataset);
 */

class NL2SPARQLGenerator {
    constructor(config) {
      this.config = config;
      this.prefixes = config.prefixes || {};
      this.entityExamples = config.entityExamples || [];
      this.schemaInfo = config.schemaInfo || {};
      this.templates = this.initializeTemplates();
      this.variationGenerator = new VariationGenerator();
    }
  
    /**
     * Initialize question-query template pairs for different complexity levels
     */
    initializeTemplates() {
      // Basic templates that work with most knowledge graphs
      const basicTemplates = [
        // Simple entity retrieval templates
        {
          id: "simple-property",
          category: "simple",
          questionTemplate: "What is the {property} of {entity}?",
          sparqlTemplate: `
            SELECT ?value WHERE {
              {entity} {property} ?value .
            }
          `,
          complexity: "basic",
          applicableProperties: ["name", "label", "title", "description"]
        },
        {
          id: "simple-inverse-property",
          category: "simple",
          questionTemplate: "Which {subjectType} has {property} {value}?",
          sparqlTemplate: `
            SELECT ?entity WHERE {
              ?entity a {subjectType} .
              ?entity {property} {value} .
            }
          `,
          complexity: "basic"
        },
        
        // Logical reasoning templates
        {
          id: "logical-and",
          category: "logical",
          questionTemplate: "Which {objectType} are both {property1} of {entity1} and {property2} of {entity2}?",
          sparqlTemplate: `
            SELECT DISTINCT ?obj WHERE {
              {entity1} {property1} ?obj .
              {entity2} {property2} ?obj .
              ?obj a {objectType} .
            }
          `,
          complexity: "intermediate"
        },
        {
          id: "logical-or",
          category: "logical",
          questionTemplate: "Which {objectType} are either {property1} of {entity1} or {property2} of {entity2}?",
          sparqlTemplate: `
            SELECT DISTINCT ?obj WHERE {
              {
                {entity1} {property1} ?obj .
              } UNION {
                {entity2} {property2} ?obj .
              }
              ?obj a {objectType} .
            }
          `,
          complexity: "intermediate"
        },
        {
          id: "logical-not",
          category: "logical",
          questionTemplate: "Which {objectType} are {property1} of {entity1} but not {property2} of {entity2}?",
          sparqlTemplate: `
            SELECT DISTINCT ?obj WHERE {
              {entity1} {property1} ?obj .
              ?obj a {objectType} .
              FILTER NOT EXISTS {
                {entity2} {property2} ?obj .
              }
            }
          `,
          complexity: "intermediate"
        },
        
        // Quantitative templates
        {
          id: "count-simple",
          category: "quantitative",
          questionTemplate: "How many {objectType} are {property} of {entity}?",
          sparqlTemplate: `
            SELECT (COUNT(DISTINCT ?obj) AS ?count) WHERE {
              {entity} {property} ?obj .
              ?obj a {objectType} .
            }
          `,
          complexity: "intermediate"
        },
        {
          id: "count-complex",
          category: "quantitative",
          questionTemplate: "How many {objectType} are both {property1} of {entity1} and {property2} of {entity2}?",
          sparqlTemplate: `
            SELECT (COUNT(DISTINCT ?obj) AS ?count) WHERE {
              {entity1} {property1} ?obj .
              {entity2} {property2} ?obj .
              ?obj a {objectType} .
            }
          `,
          complexity: "advanced"
        },
        
        // Comparative templates
        {
          id: "superlative-max",
          category: "comparative",
          questionTemplate: "Which {subjectType} has the highest {numericProperty}?",
          sparqlTemplate: `
            SELECT ?entity (MAX(?value) AS ?maxValue) WHERE {
              ?entity a {subjectType} .
              ?entity {numericProperty} ?value .
            }
            ORDER BY DESC(?maxValue)
            LIMIT 1
          `,
          complexity: "advanced",
          requiresNumericProperty: true
        },
        {
          id: "superlative-min",
          category: "comparative",
          questionTemplate: "Which {subjectType} has the lowest {numericProperty}?",
          sparqlTemplate: `
            SELECT ?entity (MIN(?value) AS ?minValue) WHERE {
              ?entity a {subjectType} .
              ?entity {numericProperty} ?value .
            }
            ORDER BY ASC(?minValue)
            LIMIT 1
          `,
          complexity: "advanced",
          requiresNumericProperty: true
        },
        {
          id: "comparative-greater-than",
          category: "comparative",
          questionTemplate: "Which {subjectType} have {numericProperty} greater than {value}?",
          sparqlTemplate: `
            SELECT ?entity ?value WHERE {
              ?entity a {subjectType} .
              ?entity {numericProperty} ?value .
              FILTER(?value > {value})
            }
            ORDER BY DESC(?value)
          `,
          complexity: "advanced",
          requiresNumericProperty: true
        },
        
        // Filter templates
        {
          id: "filter-date",
          category: "filter",
          questionTemplate: "Which {subjectType} were {dateProperty} after {date}?",
          sparqlTemplate: `
            SELECT ?entity ?date WHERE {
              ?entity a {subjectType} .
              ?entity {dateProperty} ?date .
              FILTER(?date > "{date}"^^xsd:dateTime)
            }
            ORDER BY ?date
          `,
          complexity: "advanced",
          requiresDateProperty: true
        },
        {
          id: "filter-text",
          category: "filter",
          questionTemplate: "Which {subjectType} have {textProperty} containing the word '{text}'?",
          sparqlTemplate: `
            SELECT ?entity ?text WHERE {
              ?entity a {subjectType} .
              ?entity {textProperty} ?text .
              FILTER(CONTAINS(LCASE(?text), LCASE("{text}")))
            }
          `,
          complexity: "advanced"
        },
        
        // Path templates
        {
          id: "path-two-hop",
          category: "path",
          questionTemplate: "What are the {property2} of the {property1} of {entity}?",
          sparqlTemplate: `
            SELECT DISTINCT ?final WHERE {
              {entity} {property1} ?intermediate .
              ?intermediate {property2} ?final .
            }
          `,
          complexity: "advanced"
        },
        {
          id: "path-three-hop",
          category: "path",
          questionTemplate: "What are the {property3} of the {property2} of the {property1} of {entity}?",
          sparqlTemplate: `
            SELECT DISTINCT ?final WHERE {
              {entity} {property1} ?intermediate1 .
              ?intermediate1 {property2} ?intermediate2 .
              ?intermediate2 {property3} ?final .
            }
          `,
          complexity: "expert"
        }
      ];
      
      // Merge with any custom templates provided in config
      return [...basicTemplates, ...(this.config.customTemplates || [])];
    }
  
    /**
     * Generate dataset based on knowledge graph schema
     * @param {Object} options - Generation options
     * @returns {Array} - Array of question-query pairs
     */
    generateDataset(options = {}) {
      const {
        size = 1000,
        complexityDistribution = { basic: 0.5, intermediate: 0.3, advanced: 0.15, expert: 0.05 },
        includeVariations = true,
        variationsPerQuestion = 3,
        validateQueries = false
      } = options;
      
      const dataset = [];
      let id = 1;
      
      // Calculate how many questions of each complexity to generate
      const countsByComplexity = {};
      Object.keys(complexityDistribution).forEach(complexity => {
        countsByComplexity[complexity] = Math.floor(size * complexityDistribution[complexity]);
      });
      
      // Generate questions for each complexity level
      Object.keys(countsByComplexity).forEach(complexity => {
        const count = countsByComplexity[complexity];
        const eligibleTemplates = this.templates.filter(t => t.complexity === complexity);
        
        if (eligibleTemplates.length === 0) {
          console.warn(`No templates found for complexity level: ${complexity}`);
          return;
        }
        
        for (let i = 0; i < count; i++) {
          if (dataset.length >= size) break;
          
          // Randomly select a template for this complexity level
          const templateIndex = Math.floor(Math.random() * eligibleTemplates.length);
          const template = eligibleTemplates[templateIndex];
          
          try {
            // Instantiate the template
            const instance = this.instantiateTemplate(template);
            
            if (instance) {
              // Add the base question-query pair
              dataset.push({
                id: `q${id++}`,
                question: instance.question,
                sparql: instance.sparql,
                category: template.category,
                complexity: template.complexity,
                templateId: template.id
              });
              
              // Add variations if requested
              if (includeVariations && instance.question) {
                const variations = this.variationGenerator.generateVariations(
                  instance.question, 
                  template.category,
                  Math.min(variationsPerQuestion, 5)
                );
                
                variations.forEach(variation => {
                  if (dataset.length >= size) return;
                  
                  dataset.push({
                    id: `q${id++}`,
                    question: variation,
                    sparql: instance.sparql,
                    category: template.category,
                    complexity: template.complexity,
                    templateId: template.id,
                    isVariation: true
                  });
                });
              }
            }
          } catch (error) {
            console.warn(`Error instantiating template ${template.id}: ${error.message}`);
          }
        }
      });
      
      // Validate queries if requested
      if (validateQueries && this.config.queryValidator) {
        return dataset.filter(item => {
          try {
            return this.config.queryValidator(item.sparql);
          } catch (error) {
            console.warn(`Invalid SPARQL query for id ${item.id}: ${error.message}`);
            return false;
          }
        });
      }
      
      return dataset;
    }
    
    /**
     * Instantiate a template with specific entities and properties
     * @param {Object} template - The template to instantiate
     * @returns {Object|null} - The instantiated question and SPARQL query
     */
    instantiateTemplate(template) {
      // Select entities and properties appropriate for this template
      const placeholders = this.extractPlaceholders(template);
      const replacements = this.selectReplacements(placeholders, template);
      
      if (!replacements) {
        return null;
      }
      
      // Apply replacements to the question template
      let question = template.questionTemplate;
      let sparql = template.sparqlTemplate;
      
      // Add prefixes to SPARQL query
      let prefixString = '';
      Object.entries(this.prefixes).forEach(([prefix, uri]) => {
        prefixString += `PREFIX ${prefix}: <${uri}>\n`;
      });
      sparql = prefixString + sparql;
      
      // Replace placeholders in question and query
      Object.entries(replacements).forEach(([placeholder, replacement]) => {
        const regex = new RegExp(`{${placeholder}}`, 'g');
        question = question.replace(regex, replacement.label || replacement.value);
        
        // For SPARQL, use the URI or full representation
        if (replacement.uri) {
          sparql = sparql.replace(regex, `<${replacement.uri}>`);
        } else if (replacement.sparqlValue) {
          sparql = sparql.replace(regex, replacement.sparqlValue);
        } else {
          sparql = sparql.replace(regex, replacement.value);
        }
      });
      
      // Format the SPARQL query for readability
      sparql = this.formatSparql(sparql);
      
      return { question, sparql };
    }
    
    /**
     * Extract all placeholders from template
     * @param {Object} template - Template with question and SPARQL
     * @returns {Set} - Set of placeholder names
     */
    extractPlaceholders(template) {
      const placeholders = new Set();
      const regex = /{([^}]+)}/g;
      
      let match;
      // Search in question template
      while ((match = regex.exec(template.questionTemplate)) !== null) {
        placeholders.add(match[1]);
      }
      
      // Reset regex and search in SPARQL template
      regex.lastIndex = 0;
      while ((match = regex.exec(template.sparqlTemplate)) !== null) {
        placeholders.add(match[1]);
      }
      
      return placeholders;
    }
    
    /**
     * Select appropriate replacements for template placeholders
     * @param {Set} placeholders - Set of placeholder names
     * @param {Object} template - The template being instantiated
     * @returns {Object|null} - Map of placeholder to replacement value
     */
    selectReplacements(placeholders, template) {
      const replacements = {};
      
      // Try to select appropriate values for each placeholder
      for (const placeholder of placeholders) {
        let replacement = null;
        
        // Handle entity placeholders
        if (placeholder.startsWith('entity')) {
          replacement = this.selectRandomEntity();
        } 
        // Handle property placeholders
        else if (placeholder.startsWith('property')) {
          replacement = this.selectRandomProperty(template, placeholder);
        }
        // Handle type placeholders
        else if (placeholder.endsWith('Type')) {
          replacement = this.selectRandomType(placeholder);
        }
        // Handle value placeholders
        else if (placeholder === 'value' || placeholder.endsWith('Value')) {
          replacement = this.selectRandomValue(template);
        }
        // Handle date placeholders
        else if (placeholder === 'date' || placeholder.endsWith('Date')) {
          replacement = this.generateRandomDate();
        }
        // Handle text placeholder
        else if (placeholder === 'text') {
          replacement = { value: this.generateRandomSearchTerm(), label: this.generateRandomSearchTerm() };
        }
        // Handle numeric placeholders
        else if (placeholder.startsWith('numeric') || placeholder.endsWith('Number')) {
          replacement = { value: Math.floor(Math.random() * 100), label: Math.floor(Math.random() * 100) };
        }
        
        // If we couldn't find a replacement, return null
        if (!replacement) {
          console.warn(`Could not find replacement for placeholder: ${placeholder}`);
          return null;
        }
        
        replacements[placeholder] = replacement;
      }
      
      return replacements;
    }
    
    /**
     * Select a random entity from available examples
     * @returns {Object} - Selected entity
     */
    selectRandomEntity() {
      if (this.entityExamples.length === 0) {
        return this.generateDummyEntity();
      }
      
      const index = Math.floor(Math.random() * this.entityExamples.length);
      return this.entityExamples[index];
    }
    
    /**
     * Select a random property appropriate for the template
     * @param {Object} template - The template being instantiated
     * @param {String} placeholder - The property placeholder name
     * @returns {Object} - Selected property
     */
    selectRandomProperty(template, placeholder) {
      // Check if template has specific applicable properties for this placeholder
      const propKey = `applicable${placeholder.charAt(0).toUpperCase() + placeholder.slice(1)}s`;
      
      if (template[propKey] && template[propKey].length > 0) {
        const propertyName = template[propKey][Math.floor(Math.random() * template[propKey].length)];
        return this.findPropertyByName(propertyName) || this.generateDummyProperty(propertyName);
      }
      
      // Check if we have numeric, date, or text property requirements
      if (placeholder.startsWith('numeric') && this.schemaInfo.numericProperties) {
        return this.selectRandomFromArray(this.schemaInfo.numericProperties);
      }
      
      if (placeholder.startsWith('date') && this.schemaInfo.dateProperties) {
        return this.selectRandomFromArray(this.schemaInfo.dateProperties);
      }
      
      if (placeholder.startsWith('text') && this.schemaInfo.textProperties) {
        return this.selectRandomFromArray(this.schemaInfo.textProperties);
      }
      
      // Fall back to general properties
      if (this.schemaInfo.properties && this.schemaInfo.properties.length > 0) {
        return this.selectRandomFromArray(this.schemaInfo.properties);
      }
      
      // Generate a dummy property if nothing else available
      return this.generateDummyProperty();
    }
    
    /**
     * Select a random entity type
     * @param {String} placeholder - The type placeholder
     * @returns {Object} - Selected type
     */
    selectRandomType(placeholder) {
      if (this.schemaInfo.types && this.schemaInfo.types.length > 0) {
        return this.selectRandomFromArray(this.schemaInfo.types);
      }
      
      // Generate dummy types with appropriate labels
      const typeMappings = {
        'subjectType': ['Person', 'Organization', 'Place', 'Event'],
        'objectType': ['Book', 'Movie', 'Product', 'Artwork'],
        'entityType': ['Entity', 'Thing', 'Object', 'Item']
      };
      
      // Find the best match from mappings
      for (const [typeKey, options] of Object.entries(typeMappings)) {
        if (placeholder.includes(typeKey)) {
          const label = options[Math.floor(Math.random() * options.length)];
          return {
            value: label.toLowerCase(),
            label,
            uri: `http://example.org/ontology/${label}`,
            sparqlValue: `<http://example.org/ontology/${label}>`
          };
        }
      }
      
      // Default dummy type
      return {
        value: 'thing',
        label: 'Thing',
        uri: 'http://example.org/ontology/Thing',
        sparqlValue: '<http://example.org/ontology/Thing>'
      };
    }
    
    /**
     * Select a random appropriate value
     * @param {Object} template - The template being instantiated
     * @returns {Object} - Selected value
     */
    selectRandomValue(template) {
      // Generate different kinds of values based on template category
      if (template.requiresNumericProperty) {
        const value = Math.floor(Math.random() * 1000);
        return { value, label: value.toString() };
      }
      
      if (template.requiresDateProperty) {
        return this.generateRandomDate();
      }
      
      // Default to a string value
      const options = ['name', 'title', 'description', 'identifier', 'location'];
      const value = options[Math.floor(Math.random() * options.length)];
      return { value: `"${value}"`, label: value };
    }
    
    /**
     * Generate a random date
     * @returns {Object} - Generated date
     */
    generateRandomDate() {
      const year = 2000 + Math.floor(Math.random() * 20);
      const month = 1 + Math.floor(Math.random() * 12);
      const day = 1 + Math.floor(Math.random() * 28);
      
      const dateStr = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
      return {
        value: dateStr,
        label: dateStr,
        sparqlValue: `"${dateStr}"^^xsd:date`
      };
    }
    
    /**
     * Generate a random search term
     * @returns {String} - Generated search term
     */
    generateRandomSearchTerm() {
      const terms = ['science', 'art', 'technology', 'history', 'music', 'politics', 'nature'];
      return terms[Math.floor(Math.random() * terms.length)];
    }
    
    /**
     * Generate a dummy entity when no examples are available
     * @returns {Object} - Generated entity
     */
    generateDummyEntity() {
      const entities = [
        { value: 'dbr:Albert_Einstein', label: 'Albert Einstein', uri: 'http://dbpedia.org/resource/Albert_Einstein' },
        { value: 'dbr:New_York_City', label: 'New York City', uri: 'http://dbpedia.org/resource/New_York_City' },
        { value: 'dbr:Google', label: 'Google', uri: 'http://dbpedia.org/resource/Google' },
        { value: 'dbr:The_Beatles', label: 'The Beatles', uri: 'http://dbpedia.org/resource/The_Beatles' },
        { value: 'dbr:World_War_II', label: 'World War II', uri: 'http://dbpedia.org/resource/World_War_II' }
      ];
      
      return entities[Math.floor(Math.random() * entities.length)];
    }
    
    /**
     * Generate a dummy property
     * @param {String} name - Optional property name
     * @returns {Object} - Generated property
     */
    generateDummyProperty(name) {
      const properties = [
        { value: 'dbo:birthPlace', label: 'birth place', uri: 'http://dbpedia.org/ontology/birthPlace' },
        { value: 'dbo:director', label: 'director', uri: 'http://dbpedia.org/ontology/director' },
        { value: 'dbo:author', label: 'author', uri: 'http://dbpedia.org/ontology/author' },
        { value: 'dbo:country', label: 'country', uri: 'http://dbpedia.org/ontology/country' },
        { value: 'dbo:populationTotal', label: 'population', uri: 'http://dbpedia.org/ontology/populationTotal' }
      ];
      
      if (name) {
        return {
          value: `dbo:${name}`,
          label: name.replace(/([A-Z])/g, ' $1').trim().toLowerCase(),
          uri: `http://dbpedia.org/ontology/${name}`
        };
      }
      
      return properties[Math.floor(Math.random() * properties.length)];
    }
    
    /**
     * Find a property by name in schema info
     * @param {String} name - Property name to find
     * @returns {Object|null} - Found property or null
     */
    findPropertyByName(name) {
      if (!this.schemaInfo.properties) return null;
      
      return this.schemaInfo.properties.find(p => 
        p.value === name || 
        p.label.toLowerCase() === name.toLowerCase()
      );
    }
    
    /**
     * Select a random item from an array
     * @param {Array} array - Array to select from
     * @returns {*} - Random item
     */
    selectRandomFromArray(array) {
      if (!array || array.length === 0) return null;
      return array[Math.floor(Math.random() * array.length)];
    }
    
    /**
     * Format SPARQL query for readability
     * @param {String} sparql - Raw SPARQL query
     * @returns {String} - Formatted SPARQL query
     */
    formatSparql(sparql) {
      return sparql
        .replace(/\s+/g, ' ')
        .replace(/\s*\.\s*/g, ' . ')
        .replace(/\s*{\s*/g, ' { ')
        .replace(/\s*}\s*/g, ' } ')
        .replace(/\s*SELECT/g, 'SELECT')
        .replace(/\s*WHERE/g, '\nWHERE')
        .replace(/\s*FILTER/g, '\n  FILTER')
        .replace(/\s*ORDER BY/g, '\nORDER BY')
        .replace(/\s*LIMIT/g, '\nLIMIT')
        .replace(/\s*GROUP BY/g, '\nGROUP BY')
        .replace(/\s*HAVING/g, '\nHAVING')
        .trim();
    }
    
    /**
     * Export dataset to JSON format
     * @param {Array} dataset - Generated dataset
     * @returns {String} - JSON string
     */
    exportJSON(dataset) {
      return JSON.stringify(dataset, null, 2);
    }
    
    /**
     * Export dataset to CSV format
     * @param {Array} dataset - Generated dataset
     * @returns {String} - CSV string
     */
    exportCSV(dataset) {
      const header = 'id,question,sparql,category,complexity,templateId\n';
      const rows = dataset.map(item => {
        const sparqlEscaped = item.sparql.replace(/"/g, '""').replace(/\n/g, ' ');
        return `${item.id},"${item.question}","${sparqlEscaped}",${item.category},${item.complexity},${item.templateId}`;
      });
      
      return header + rows.join('\n');
    }
    
    /**
     * Export dataset to JSONL format (one JSON object per line)
     * @param {Array} dataset - Generated dataset
     * @returns {String} - JSONL string
     */
    exportJSONL(dataset) {
      return dataset.map(item => JSON.stringify(item)).join('\n');
    }
  }
  
  /**
   * Generates variations of natural language questions
   */
  class VariationGenerator {
    /**
     * Generate variations of a question
     * @param {String} question - Original question
     * @param {String} category - Question category
     * @param {Number} count - Number of variations to generate
     * @returns {Array} - Array of variation strings
     */
    generateVariations(question, category, count = 3) {
      const variations = [];
      
      // Add standard variations based on category
      const categoryVariations = this.getCategoryVariations(question, category);
      variations.push(...categoryVariations);
      
      // Add general variations
      variations.push(...this.getGeneralVariations(question));
      
      // Ensure we don't have duplicate variations
      const uniqueVariations = [...new Set(variations)];
      
      // Return requested number of variations (or fewer if not enough generated)
      return uniqueVariations.slice(0, Math.min(count, uniqueVariations.length));
    }
    
    /**
     * Get category-specific variations
     * @param {String} question - Original question
     * @param {String} category - Question category
     * @returns {Array} - Array of variation strings
     */
    getCategoryVariations(question, category) {
      switch (category) {
        case 'simple':
          return this.getSimpleVariations(question);
        case 'logical':
          return this.getLogicalVariations(question);
        case 'quantitative':
          return this.getQuantitativeVariations(question);
        case 'comparative':
          return this.getComparativeVariations(question);
        case 'filter':
          return this.getFilterVariations(question);
        case 'path':
          return this.getPathVariations(question);
        default:
          return [];
      }
    }
    
    /**
   * Get variations for simple questions
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getSimpleVariations(question) {
    const variations = [];
    
    // What is -> What's
    variations.push(question.replace('What is', "What's"));
    
    // Adding "Can you tell me"
    if (question.startsWith('What')) {
      variations.push(`Can you tell me ${question.toLowerCase()}`);
    }
    
    // Adding "I want to know"
    variations.push(`I want to know ${question.toLowerCase().replace('?', '.')}`);
    
    return variations;
  }
  
  /**
   * Get variations for logical questions
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getLogicalVariations(question) {
    const variations = [];
    
    // Replace "which" with "what"
    variations.push(question.replace(/Which/i, 'What'));
    
    // Add "Could you list"
    if (question.startsWith('Which')) {
      variations.push(`Could you list ${question.toLowerCase().replace('?', '?')}`);
    }
    
    return variations;
  }
  
  /**
   * Get variations for quantitative questions
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getQuantitativeVariations(question) {
    const variations = [];
    
    // How many -> What is the number of
    variations.push(question.replace('How many', 'What is the number of'));
    
    // How many -> Count the
    variations.push(question.replace('How many', 'Count the'));
    
    return variations;
  }
  
  /**
   * Get variations for comparative questions
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getComparativeVariations(question) {
    const variations = [];
    
    // Which X has the highest -> What is the X with the highest
    variations.push(question.replace(/Which (.*?) has the highest/i, 'What is the $1 with the highest'));
    
    // Which X has the lowest -> What is the X with the lowest
    variations.push(question.replace(/Which (.*?) has the lowest/i, 'What is the $1 with the lowest'));
    
    return variations;
  }
  
  /**
   * Get variations for filter questions
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getFilterVariations(question) {
    const variations = [];
    
    // Which -> List all
    variations.push(question.replace(/Which/i, 'List all'));
    
    // Which -> Give me
    variations.push(question.replace(/Which/i, 'Give me all'));
    
    return variations;
  }
  
  /**
   * Get variations for path questions
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getPathVariations(question) {
    const variations = [];
    
    // What are -> Show me
    variations.push(question.replace(/What are/i, 'Show me'));
    
    // What are -> List
    variations.push(question.replace(/What are/i, 'List'));
    
    return variations;
  }
  
  /**
   * Get general variations that apply to any question
   * @param {String} question - Original question
   * @returns {Array} - Array of variation strings
   */
  getGeneralVariations(question) {
    const variations = [];
    
    // Add please
    if (question.endsWith('?')) {
      variations.push(question.replace('?', ' please?'));
    }
    
    // Do you know...
    variations.push(`Do you know ${question.toLowerCase()}`);
    
    // Can you find...
    if (question.startsWith('What') || question.startsWith('Which')) {
      variations.push(`Can you find ${question.toLowerCase()}`);
    }
    
    return variations;
  }
}

// Export the class
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { NL2SPARQLGenerator, VariationGenerator };
}