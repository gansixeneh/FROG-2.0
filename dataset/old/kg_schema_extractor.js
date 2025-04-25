/**
 * Knowledge Graph Schema Extractor
 * 
 * This utility helps extract schema information from a knowledge graph
 * to configure the NL2SPARQL Generator.
 * 
 * It works with:
 * 1. SPARQL endpoints
 * 2. RDF files (Turtle, N-Triples, RDF/XML)
 * 3. JSON-LD data
 */

const N3 = require('n3');

class KGSchemaExtractor {
    /**
     * Create a new schema extractor
     * @param {Object} options - Configuration options
     */
    constructor(options = {}) {
      this.options = {
        sparqlEndpoint: null,
        sampleSize: 1000,
        prefixes: {
          'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
          'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
          'owl': 'http://www.w3.org/2002/07/owl#',
          'xsd': 'http://www.w3.org/2001/XMLSchema#'
        },
        ...options
      };
      
      this.schemaInfo = {
        properties: [],
        types: [],
        numericProperties: [],
        dateProperties: [],
        textProperties: [],
        booleanProperties: []
      };
      
      this.entityExamples = [];
      this.fetch = typeof window !== 'undefined' ? window.fetch : require('node-fetch');
    }
    
    /**
     * Extract schema from a SPARQL endpoint
     * @param {String} endpoint - URL of the SPARQL endpoint
     * @returns {Object} - Extracted schema info
     */
    async extractFromEndpoint(endpoint) {
      console.log(`Extracting schema from SPARQL endpoint: ${endpoint}`);
      this.options.sparqlEndpoint = endpoint;
      
      try {
        await this.extractClasses();
        await this.extractProperties();
        await this.extractPropertyTypes();
        await this.extractEntityExamples();
        
        return {
          schemaInfo: this.schemaInfo,
          entityExamples: this.entityExamples,
          prefixes: this.options.prefixes
        };
      } catch (error) {
        console.error('Error extracting schema:', error);
        throw error;
      }
    }
    
    /**
     * Extract schema from an RDF file
     * @param {String} filePath - Path to the RDF file
     * @param {String} format - Format of the file (turtle, n-triples, rdf-xml)
     * @returns {Object} - Extracted schema info
     */
    async extractFromFile(filePath, format = 'turtle') {
      console.log(`Extracting schema from RDF file: ${filePath} (${format})`);
      
      try {
        // In a browser environment, you would use FileReader
        // In Node.js, you would use fs.readFile
        // This is a simplified placeholder implementation
        const data = await this.readFile(filePath);
        return this.extractFromString(data, format);
      } catch (error) {
        console.error('Error extracting schema from file:', error);
        throw error;
      }
    }
    
    /**
     * Extract schema from RDF string content
     * @param {String} content - RDF content as string
     * @param {String} format - Format of the content (turtle, n-triples, rdf-xml, jsonld)
     * @returns {Object} - Extracted schema info
     */
    async extractFromString(content, format) {
      console.log(`Extracting schema from RDF string (${format})`);
      
      try {
        const schema = await this.parseRdfContent(content, format);
        
        return {
          schemaInfo: schema,
          entityExamples: this.entityExamples,
          prefixes: this.options.prefixes
        };
      } catch (error) {
        console.error('Error extracting schema from string:', error);
        throw error;
      }
    }
    
    /**
     * Execute a SPARQL query against the configured endpoint
     * @param {String} query - SPARQL query to execute
     * @returns {Object} - Query results
     */
    async executeSparqlQuery(query) {
      if (!this.options.sparqlEndpoint) {
        throw new Error('No SPARQL endpoint configured');
      }
      
      const params = new URLSearchParams();
      params.append('query', query);
      params.append('format', 'json');
      
      const response = await this.fetch(this.options.sparqlEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/sparql-results+json'
        },
        body: params
      });
      
      if (!response.ok) {
        throw new Error(`SPARQL query failed: ${response.statusText}`);
      }
      
      return await response.json();
    }
    
    /**
     * Extract classes/types from the knowledge graph
     */
    async extractClasses() {
      console.log('Extracting classes/types...');
      
      const prefixes = this.getPrefixString();
      const query = `
        ${prefixes}
        SELECT DISTINCT ?class ?label
        WHERE {
          {
            ?class a rdfs:Class .
            OPTIONAL { ?class rdfs:label ?label }
          }
          UNION 
          {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
          }
        }
        LIMIT ${this.options.sampleSize}
      `;
      
      try {
        const result = await this.executeSparqlQuery(query);
        
        this.schemaInfo.types = result.results.bindings.map(binding => {
          const uri = binding.class.value;
          const label = binding.label ? binding.label.value : this.extractLabelFromUri(uri);
          
          return {
            value: this.shortenUri(uri),
            label: label,
            uri: uri
          };
        });
        
        console.log(`Extracted ${this.schemaInfo.types.length} classes/types`);
      } catch (error) {
        console.error('Error extracting classes:', error);
      }
    }
    
    /**
     * Extract properties from the knowledge graph
     */
    async extractProperties() {
      console.log('Extracting properties...');
      
      const prefixes = this.getPrefixString();
      const query = `
        ${prefixes}
        SELECT DISTINCT ?property ?label ?domain ?range
        WHERE {
          {
            ?property a rdf:Property .
            OPTIONAL { ?property rdfs:label ?label }
            OPTIONAL { ?property rdfs:domain ?domain }
            OPTIONAL { ?property rdfs:range ?range }
          }
          UNION 
          {
            ?property a owl:ObjectProperty .
            OPTIONAL { ?property rdfs:label ?label }
            OPTIONAL { ?property rdfs:domain ?domain }
            OPTIONAL { ?property rdfs:range ?range }
          }
          UNION 
          {
            ?property a owl:DatatypeProperty .
            OPTIONAL { ?property rdfs:label ?label }
            OPTIONAL { ?property rdfs:domain ?domain }
            OPTIONAL { ?property rdfs:range ?range }
          }
        }
        LIMIT ${this.options.sampleSize}
      `;
      
      try {
        const result = await this.executeSparqlQuery(query);
        
        this.schemaInfo.properties = result.results.bindings.map(binding => {
          const uri = binding.property.value;
          const label = binding.label ? binding.label.value : this.extractLabelFromUri(uri);
          
          return {
            value: this.shortenUri(uri),
            label: label,
            uri: uri,
            domain: binding.domain ? binding.domain.value : null,
            range: binding.range ? binding.range.value : null
          };
        });
        
        console.log(`Extracted ${this.schemaInfo.properties.length} properties`);
      } catch (error) {
        console.error('Error extracting properties:', error);
      }
    }
    
    /**
     * Categorize properties by their range types (numeric, date, text, etc.)
     */
    async extractPropertyTypes() {
      console.log('Categorizing properties by type...');
      
      // First, check the range of properties from schema info
      for (const property of this.schemaInfo.properties) {
        if (property.range) {
          this.categorizePropertyByRange(property);
        }
      }
      
      // Then, examine actual property values in the data
      await this.examinePropertyValues();
      
      console.log(`Categorized properties: 
        - Numeric: ${this.schemaInfo.numericProperties.length}
        - Date: ${this.schemaInfo.dateProperties.length}
        - Text: ${this.schemaInfo.textProperties.length}
        - Boolean: ${this.schemaInfo.booleanProperties.length}`);
    }
    
    /**
     * Categorize a property based on its rdfs:range
     * @param {Object} property - Property to categorize
     */
    categorizePropertyByRange(property) {
      const range = property.range;
      
      // Numeric ranges
      if (range === 'http://www.w3.org/2001/XMLSchema#integer' || 
          range === 'http://www.w3.org/2001/XMLSchema#decimal' ||
          range === 'http://www.w3.org/2001/XMLSchema#float' ||
          range === 'http://www.w3.org/2001/XMLSchema#double') {
        this.addToPropertyCategory('numericProperties', property);
      }
      // Date ranges
      else if (range === 'http://www.w3.org/2001/XMLSchema#date' ||
               range === 'http://www.w3.org/2001/XMLSchema#dateTime' ||
               range === 'http://www.w3.org/2001/XMLSchema#time') {
        this.addToPropertyCategory('dateProperties', property);
      }
      // Text ranges
      else if (range === 'http://www.w3.org/2001/XMLSchema#string' ||
               range === 'http://www.w3.org/2000/01/rdf-schema#Literal') {
        this.addToPropertyCategory('textProperties', property);
      }
      // Boolean ranges
      else if (range === 'http://www.w3.org/2001/XMLSchema#boolean') {
        this.addToPropertyCategory('booleanProperties', property);
      }
    }
    
    /**
     * Add a property to a specific category
     * @param {String} category - Category name
     * @param {Object} property - Property to add
     */
    addToPropertyCategory(category, property) {
      // Check if property already exists in the category
      const exists = this.schemaInfo[category].some(p => p.uri === property.uri);
      if (!exists) {
        this.schemaInfo[category].push(property);
      }
    }
    
    /**
     * Examine property values in the data to determine property types
     */
    async examinePropertyValues() {
      console.log('Examining property values to determine types...');
      
      // For each property that hasn't been categorized yet
      const uncategorizedProperties = this.schemaInfo.properties.filter(p => 
        !this.schemaInfo.numericProperties.some(np => np.uri === p.uri) &&
        !this.schemaInfo.dateProperties.some(dp => dp.uri === p.uri) &&
        !this.schemaInfo.textProperties.some(tp => tp.uri === p.uri) &&
        !this.schemaInfo.booleanProperties.some(bp => bp.uri === p.uri)
      );
      
      for (const property of uncategorizedProperties) {
        try {
          await this.categorizePropertyByValues(property);
        } catch (error) {
          console.warn(`Error categorizing property ${property.uri}: ${error.message}`);
        }
      }
    }
    
    /**
     * Categorize a property by examining its values
     * @param {Object} property - Property to categorize
     */
    async categorizePropertyByValues(property) {
      const prefixes = this.getPrefixString();
      const propertyUri = property.uri;
      
      const query = `
        ${prefixes}
        SELECT ?value (DATATYPE(?value) as ?datatype)
        WHERE {
          ?s <${propertyUri}> ?value .
        }
        LIMIT 100
      `;
      
      try {
        const result = await this.executeSparqlQuery(query);
        
        if (result.results.bindings.length === 0) {
          return; // No values found
        }
        
        // Count occurrences of each datatype
        const datatypeCounts = {};
        
        for (const binding of result.results.bindings) {
          if (binding.datatype) {
            const datatype = binding.datatype.value;
            datatypeCounts[datatype] = (datatypeCounts[datatype] || 0) + 1;
          } else {
            // If no datatype, try to infer from the value
            const value = binding.value.value;
            
            if (!isNaN(Number(value))) {
              datatypeCounts['numeric'] = (datatypeCounts['numeric'] || 0) + 1;
            } else if (this.isDateString(value)) {
              datatypeCounts['date'] = (datatypeCounts['date'] || 0) + 1;
            } else if (value === 'true' || value === 'false') {
              datatypeCounts['boolean'] = (datatypeCounts['boolean'] || 0) + 1;
            } else {
              datatypeCounts['text'] = (datatypeCounts['text'] || 0) + 1;
            }
          }
        }
        
        // Determine the most common datatype
        let mostCommonType = null;
        let maxCount = 0;
        
        for (const [type, count] of Object.entries(datatypeCounts)) {
          if (count > maxCount) {
            mostCommonType = type;
            maxCount = count;
          }
        }
        
        // Categorize based on the most common datatype
        if (mostCommonType) {
          if (mostCommonType.includes('integer') || 
              mostCommonType.includes('decimal') || 
              mostCommonType.includes('float') || 
              mostCommonType.includes('double') ||
              mostCommonType === 'numeric') {
            this.addToPropertyCategory('numericProperties', property);
          } else if (mostCommonType.includes('date') || 
                    mostCommonType.includes('time')) {
            this.addToPropertyCategory('dateProperties', property);
          } else if (mostCommonType.includes('boolean')) {
            this.addToPropertyCategory('booleanProperties', property);
          } else {
            this.addToPropertyCategory('textProperties', property);
          }
        }
      } catch (error) {
        console.warn(`Could not examine values for property ${propertyUri}: ${error.message}`);
      }
    }
    
    /**
     * Extract entity examples for the dataset
     */
    async extractEntityExamples() {
      console.log('Extracting entity examples...');
      
      // Extract examples for each class/type
      for (const type of this.schemaInfo.types) {
        try {
          await this.extractExamplesForType(type);
        } catch (error) {
          console.warn(`Error extracting examples for type ${type.uri}: ${error.message}`);
        }
      }
      
      console.log(`Extracted ${this.entityExamples.length} entity examples`);
    }
    
    /**
     * Extract example entities for a specific type
     * @param {Object} type - The entity type
     */
    async extractExamplesForType(type) {
      const prefixes = this.getPrefixString();
      const typeUri = type.uri;
      
      const query = `
        ${prefixes}
        SELECT DISTINCT ?entity ?label
        WHERE {
          ?entity a <${typeUri}> .
          OPTIONAL { ?entity rdfs:label ?label }
        }
        LIMIT 10
      `;
      
      try {
        const result = await this.executeSparqlQuery(query);
        
        const examples = result.results.bindings.map(binding => {
          const uri = binding.entity.value;
          const label = binding.label ? binding.label.value : this.extractLabelFromUri(uri);
          
          return {
            value: this.shortenUri(uri),
            label: label,
            uri: uri,
            type: type.value
          };
        });
        
        this.entityExamples.push(...examples);
      } catch (error) {
        console.warn(`Could not extract examples for type ${typeUri}: ${error.message}`);
      }
    }
    
    /**
     * Check if a string resembles a date
     * @param {String} str - String to check
     * @returns {Boolean} - True if string looks like a date
     */
    isDateString(str) {
      // Simple date patterns
      const datePatterns = [
        /^\d{4}-\d{2}-\d{2}$/, // YYYY-MM-DD
        /^\d{2}\/\d{2}\/\d{4}$/, // MM/DD/YYYY
        /^\d{4}\/\d{2}\/\d{2}$/, // YYYY/MM/DD
        /^\d{2}-\d{2}-\d{4}$/, // MM-DD-YYYY
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/ // ISO date with time
      ];
      
      return datePatterns.some(pattern => pattern.test(str));
    }
    
    /**
     * Extract a label from a URI
     * @param {String} uri - URI to extract label from
     * @returns {String} - Extracted label
     */
    extractLabelFromUri(uri) {
      // Extract the last part of the URI
      const lastPart = uri.split(/\/|#/).pop();
      
      // Remove underscores and replace with spaces
      const withSpaces = lastPart.replace(/_/g, ' ');
      
      // Convert camelCase to spaces
      return withSpaces.replace(/([a-z])([A-Z])/g, '$1 $2');
    }
    
    /**
     * Shorten a URI using known prefixes
     * @param {String} uri - URI to shorten
     * @returns {String} - Shortened URI
     */
    shortenUri(uri) {
      for (const [prefix, namespace] of Object.entries(this.options.prefixes)) {
        if (uri.startsWith(namespace)) {
          return `${prefix}:${uri.slice(namespace.length)}`;
        }
      }
      
      return uri;
    }
    
    /**
     * Get prefixes formatted as a SPARQL prefix string
     * @returns {String} - Prefix string
     */
    getPrefixString() {
      return Object.entries(this.options.prefixes)
        .map(([prefix, namespace]) => `PREFIX ${prefix}: <${namespace}>`)
        .join('\n');
    }
    
    /**
     * Read a file (simplified implementation)
     * @param {String} filePath - Path to the file
     * @returns {Promise<String>} - File contents
     */
    async readFile(filePath) {
      // This is a placeholder - implementation would depend on environment
      if (typeof window !== 'undefined') {
        // Browser environment
        throw new Error('File reading in browser requires actual implementation');
      } else {
        // Node.js environment
        const fs = require('fs').promises;
        return await fs.readFile(filePath, 'utf8');
      }
    }
    
    /**
     * Parse RDF content based on format
     * @param {String} content - RDF content
     * @param {String} format - Format of the content
     */
    parseRdfContent(content, format) {
      return new Promise((resolve, reject) => {
        try {
          const parser = new N3.Parser({ format: format || 'Turtle' });
          const store = new N3.Store();
          
          parser.parse(content, (error, quad, prefixes) => {
            if (error) return reject(error);
            if (quad) store.addQuad(quad);
            else {
              // Parsing complete - extract schema
              const schema = {
                classes: this.extractClasses(store),
                properties: this.extractProperties(store),
                ontologies: this.extractOntologies(store)
              };
              resolve(schema);
            }
          });
        } catch (error) {
          reject(error);
        }
      });
    }

    /**
     * Extract classes from the RDF store
     * @param {Object} store - RDF store
     * @returns {Array} - Extracted classes
     */
    extractClasses(store) {
      const classes = [];
      const classQuads = store.getQuads(
        null, 
        this.createNamedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
        this.createNamedNode('http://www.w3.org/2000/01/rdf-schema#Class'),
        null
      );
      
      classQuads.forEach(quad => {
        classes.push({
          uri: quad.subject.value,
          label: this.getLabel(store, quad.subject)
        });
      });
      
      return classes;
    }

    /**
     * Extract properties from the RDF store
     * @param {Object} store - RDF store
     * @returns {Array} - Extracted properties
     */
    extractProperties(store) {
      const properties = [];
      const propertyQuads = store.getQuads(
        null,
        this.createNamedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
        this.createNamedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#Property'),
        null
      );
      
      propertyQuads.forEach(quad => {
        properties.push({
          uri: quad.subject.value,
          label: this.getLabel(store, quad.subject),
          domain: this.getPropertyDomain(store, quad.subject),
          range: this.getPropertyRange(store, quad.subject)
        });
      });
      
      return properties;
    }

    /**
     * Create a named node for RDF
     * @param {String} uri - URI for the named node
     * @returns {Object} - Named node
     */
    createNamedNode(uri) {
      return N3.DataFactory.namedNode(uri);
    }

    /**
     * Get label for a subject from the RDF store
     * @param {Object} store - RDF store
     * @param {Object} subject - RDF subject
     * @returns {String|null} - Label or null
     */
    getLabel(store, subject) {
      const labelQuads = store.getQuads(
        subject,
        this.createNamedNode('http://www.w3.org/2000/01/rdf-schema#label'),
        null,
        null
      );
      return labelQuads.length > 0 ? labelQuads[0].object.value : null;
    }

    /**
     * Get domain for a property from the RDF store
     * @param {Object} store - RDF store
     * @param {Object} property - RDF property
     * @returns {String|null} - Domain or null
     */
    getPropertyDomain(store, property) {
      const domainQuads = store.getQuads(
        property,
        this.createNamedNode('http://www.w3.org/2000/01/rdf-schema#domain'),
        null,
        null
      );
      return domainQuads.length > 0 ? domainQuads[0].object.value : null;
    }

    /**
     * Get range for a property from the RDF store
     * @param {Object} store - RDF store
     * @param {Object} property - RDF property
     * @returns {String|null} - Range or null
     */
    getPropertyRange(store, property) {
      const rangeQuads = store.getQuads(
        property,
        this.createNamedNode('http://www.w3.org/2000/01/rdf-schema#range'),
        null,
        null
      );
      return rangeQuads.length > 0 ? rangeQuads[0].object.value : null;
    }

    /**
     * Extract ontologies from the RDF store
     * @param {Object} store - RDF store
     * @returns {Array} - Extracted ontologies
     */
    extractOntologies(store) {
      // Extract ontology information if needed
      return [];
    }
  }
  
  // Export the class
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KGSchemaExtractor };
  }