# backend/agent/langgraph/utils/visualization.py
import os
import re
import html
import json
import requests
import numpy as np
from datetime import datetime
import uuid
import tempfile
import logging
from urllib.parse import urljoin
from rdflib import Graph, Namespace, RDF, RDFS, Literal
from rdflib.namespace import XSD
import asyncio
import hashlib

# Configure logging
logger = logging.getLogger(__name__)

class JenaUploader:
    """
    Class for uploading TTL data to Apache Jena Fuseki server
    """
    def __init__(self, base_url=None, dataset_name="visualization-logs"):
        # Get the base URL from environment variable or use default
        self.base_url = base_url or os.environ.get("APACHE_JENA_URL", "http://localhost:3030")
        self.dataset_name = dataset_name
        
        # Ensure base_url has no trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
            
        logger.info(f"Initialized JenaUploader with base URL: {self.base_url}")
    
    def create_dataset_if_not_exists(self):
        """Check if dataset exists, create it if not"""
        try:
            # First check if the dataset already exists
            response = requests.get(f"{self.base_url}/$/datasets")
            if response.status_code == 200:
                datasets = response.json().get("datasets", [])
                dataset_uris = [d.get("ds.name") for d in datasets]
                
                # Check if our dataset is in the list
                if f"/{self.dataset_name}" in dataset_uris:
                    logger.info(f"Dataset {self.dataset_name} already exists")
                    return True
            
            # Dataset doesn't exist, create it
            logger.info(f"Creating dataset {self.dataset_name}")
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post(
                f"{self.base_url}/$/datasets",
                headers=headers,
                data=f"dbName={self.dataset_name}&dbType=tdb2"
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"Successfully created dataset {self.dataset_name}")
                return True
            else:
                logger.error(f"Failed to create dataset: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating dataset: {e}")
            return False
    
    def upload_ttl(self, ttl_content, graph_name=None):
        """
        Upload TTL content to Jena Fuseki server
        
        Args:
            ttl_content: TTL content as string
            graph_name: Optional named graph to upload to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure dataset exists
            if not self.create_dataset_if_not_exists():
                return False
            
            # Prepare the endpoint URL
            if graph_name:
                # Upload to specific named graph
                encoded_graph = requests.utils.quote(graph_name)
                url = f"{self.base_url}/{self.dataset_name}/data?graph={encoded_graph}"
            else:
                # Upload to default graph
                url = f"{self.base_url}/{self.dataset_name}/data"
            
            # Upload the TTL content
            headers = {"Content-Type": "text/turtle"}
            response = requests.post(url, headers=headers, data=ttl_content.encode('utf-8'))
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"Successfully uploaded TTL data to {url}")
                return True
            else:
                logger.error(f"Failed to upload TTL data: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading TTL data: {e}")
            return False

class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NumPy data types and objects"""
    def default(self, obj):
        # Handle NumPy types
        if isinstance(obj, np.float32):
            return float(obj)
        if isinstance(obj, np.float64):
            return float(obj)
        if isinstance(obj, np.int32):
            return int(obj)
        if isinstance(obj, np.int64):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_, np.bool8)):
            return bool(obj)
            
        # Handle message objects
        if hasattr(obj, "__class__") and obj.__class__.__name__ in ["AIMessage", "HumanMessage", "SystemMessage", "ChatMessage"]:
            # Try to get the message content and metadata
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            elif hasattr(obj, "content"):
                result = {"content": obj.content, "type": obj.__class__.__name__}
                # Add additional attributes if they exist
                if hasattr(obj, "additional_kwargs"):
                    result["additional_kwargs"] = obj.additional_kwargs
                return result
            else:
                # Fallback to using the object's __dict__
                return obj.__dict__
                
        # Return default for any other types
        return super(CustomEncoder, self).default(obj)

class LogToRDF:
    """Convert execution logs to RDF following SLOGERT approach with sophisticated patterns"""
    
    def __init__(self, run_id=None):
        # Define namespaces
        self.LOG = Namespace("https://w3id.org/sepses/ns/log#")
        self.LOGEX = Namespace("https://w3id.org/sepses/ns/logex#")
        self.LOGID = Namespace("https://sepses.ifs.tuwien.ac.at/id/log#")  # For shared vocabulary
        self.LXID = Namespace("https://sepses.ifs.tuwien.ac.at/id/logex#")
        self.CEE = Namespace("https://cee.mitre.org/cee#")
        self.FOAF = Namespace("http://xmlns.com/foaf/0.1/")
        
        # Add a global namespace for all runs instead of run-specific namespace
        self.LOGS_NS = Namespace("https://sepses.ifs.tuwien.ac.at/id/logs/")
        
        # Generate a random UUID for this run if not provided
        self.run_id = run_id if run_id else str(uuid.uuid4())
        
        # Initialize RDF graph
        self.graph = Graph()
        self.graph.bind("log", self.LOG)
        self.graph.bind("logex", self.LOGEX)
        self.graph.bind("logid", self.LOGID)
        self.graph.bind("lxid", self.LXID)
        self.graph.bind("logs", self.LOGS_NS)
        self.graph.bind("cee", self.CEE)
        self.graph.bind("foaf", self.FOAF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        
        # Create a parent entity for all runs
        self.all_runs_uri = self.LOGS_NS["AllRuns"]
        self.graph.add((self.all_runs_uri, RDF.type, self.LOGEX.RunCollection))
        self.graph.add((self.all_runs_uri, RDFS.label, Literal("Collection of All Runs")))
        
        # Store the metadata URI for later use (using the UUID as the entity ID)
        self.metadata_uri = self.LOGS_NS[self.run_id]
        
        # Keep track of entities for deduplication
        self.entities = {}
        self.templates = {}
    
    def generate_event_id(self, event):
        """Generate unique ID for log event"""
        content = f"{event['component']}_{event['event_type']}_{event['timestamp']}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def add_log_event(self, log_entry):
        """Convert a single log entry to RDF triples with sophisticated patterns"""
        event_id = self.generate_event_id(log_entry)
        event_uri = self.LOGS_NS[f"Event_{event_id}"]
        
        # Add event type and basic properties
        self.graph.add((event_uri, RDF.type, self.LOG.Event))
        # Add reference to the run metadata entity (foreign key)
        self.graph.add((event_uri, self.LOGEX.belongsToRun, self.metadata_uri))
        
        # Add timestamp
        timestamp = datetime.fromisoformat(log_entry['timestamp'])
        self.graph.add((event_uri, self.LOG.time, Literal(timestamp, datatype=XSD.dateTime)))
        
        # Add component as process/service - use LOGID for component type (shared vocabulary)
        component = log_entry['component']
        self.graph.add((event_uri, self.LOG.pname, self.LOGID[f"{component.replace(' ', '_')}"]))
        
        # Add event type - use LOGID for event type (shared vocabulary)
        event_type = log_entry['event_type']
        event_type_uri = self.LOGID[f"EventType_{event_type.replace(' ', '_')}"]
        self.graph.add((event_uri, self.LOG.eventType, event_type_uri))
        
        # Ensure the event type exists in vocabulary
        if (event_type_uri, RDF.type, self.LOG.EventType) not in self.graph:
            self.graph.add((event_type_uri, RDF.type, self.LOG.EventType))
            self.graph.add((event_type_uri, RDFS.label, Literal(event_type)))
            self.graph.add((event_type_uri, self.LOGEX.eventCount, Literal(1)))
        else:
            # Increment event count if it exists
            count_triple = list(self.graph.triples((event_type_uri, self.LOGEX.eventCount, None)))
            if count_triple:
                old_count = int(count_triple[0][2])
                self.graph.remove((event_type_uri, self.LOGEX.eventCount, count_triple[0][2]))
                self.graph.add((event_type_uri, self.LOGEX.eventCount, Literal(old_count + 1)))
        
        # Add source information using LOGS_NS for instance data
        source_uri = self.LOGS_NS[f"Source_{component.replace(' ', '_')}"]
        self.graph.add((event_uri, self.LOG.hasSource, source_uri))
        self.graph.add((source_uri, RDF.type, self.LOG.Source))
        
        # Source type uses LOGID (vocabulary)
        source_type_uri = self.LOGID[f"SourceType_{component.replace(' ', '_')}"]
        self.graph.add((source_uri, self.LOG.hasSourceType, source_type_uri))
        
        # Process details with sophisticated patterns
        if log_entry.get('details'):
            self._process_details(event_uri, log_entry['details'], event_id)
        
        # Add duration if available
        if log_entry.get('start_time') and log_entry.get('end_time'):
            start = datetime.fromisoformat(log_entry['start_time'])
            end = datetime.fromisoformat(log_entry['end_time'])
            duration = (end - start).total_seconds()
            self.graph.add((event_uri, self.LOG.duration, Literal(duration, datatype=XSD.float)))
    
    def _process_details(self, event_uri, details, event_id):
        """Process event details with sophisticated patterns"""
        if isinstance(details, dict):
            # Handle entity extraction
            if 'entities' in details:
                self._add_entities(event_uri, details['entities'])
            
            # Handle SPARQL queries
            if 'query' in details or 'sparql' in details:
                query_text = details.get('query') or details.get('sparql')
                self._add_sparql_query(event_uri, query_text, event_id)
            
            # Handle template patterns
            if 'template' in details:
                self._add_template_pattern(event_uri, details['template'], event_id)
            
            # Handle parameters
            if 'parameters' in details or any(key.endswith('_properties') for key in details):
                self._add_parameters(event_uri, details, event_id)
            
            # Handle results
            if 'results' in details:
                self._add_results(event_uri, details['results'], event_id)
            
            # Handle approach/method used
            if 'approach' in details or 'method' in details:
                approach = details.get('approach') or details.get('method')
                self.graph.add((event_uri, self.LOG.approach, Literal(approach)))
            
            # Handle other properties like question
            if 'question' in details:
                self.graph.add((event_uri, self.LOG.hasQuestion, Literal(details['question'])))
            
            # Handle entity URI
            if 'entity_uri' in details:
                self.graph.add((event_uri, self.LOG.hasEntityUri, Literal(details['entity_uri'])))
            
            # Handle generic key-value pairs
            for key, value in details.items():
                if key not in ['entities', 'query', 'sparql', 'template', 'parameters', 'results', 
                              'approach', 'method', 'question', 'entity_uri']:
                    self._add_generic_detail(event_uri, key, value, event_id)
    
    def _add_entities(self, event_uri, entities):
        """Add extracted entities with proper typing"""
        if isinstance(entities, list):
            for entity in entities:
                entity_id = entity.replace(' ', '_')
                # Use LOGID for entity type (vocabulary), but LOGS_NS for entity instance
                entity_uri = self.LOGS_NS[f"Entity_{entity_id}"]
                
                # Check if entity already exists in this run
                if entity not in self.entities:
                    self.entities[entity] = entity_uri
                    self.graph.add((entity_uri, RDF.type, self.LOG.Entity))
                    self.graph.add((entity_uri, RDFS.label, Literal(entity)))
                    
                    # Try to determine entity type based on content
                    entity_type = self._determine_entity_type(entity)
                    if entity_type:
                        self.graph.add((entity_uri, RDF.type, entity_type))
                
                self.graph.add((event_uri, self.LOG.hasEntity, self.entities[entity]))
    
    def _determine_entity_type(self, entity):
        """Determine entity type based on content patterns"""
        # IP address pattern
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', entity):
            return self.LOG.IPv4
        
        # Port number
        if re.match(r'^\d{1,5}$', entity) and 1 <= int(entity) <= 65535:
            return self.LOG.Port
        
        # User pattern
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', entity) and len(entity) < 32:
            return self.LOG.User
        
        # URL pattern
        if re.match(r'^https?://', entity):
            return self.LOG.URL
        
        return None
    
    def _add_sparql_query(self, event_uri, query_text, event_id):
        """Add SPARQL query information"""
        # Use LOGS_NS for query instance
        query_uri = self.LOGS_NS[f"Query_{event_id}"]
        self.graph.add((event_uri, self.LOG.hasQuery, query_uri))
        self.graph.add((query_uri, RDF.type, self.LOGEX.SPARQLQuery))
        self.graph.add((query_uri, RDFS.label, Literal(query_text)))
        
        # Extract Wikidata entities and properties from query
        self._extract_wikidata_refs(query_uri, query_text)
    
    def _extract_wikidata_refs(self, query_uri, query_text):
        """Extract Wikidata entity and property references from SPARQL query"""
        # Extract Wikidata entities (Q numbers)
        entities = re.findall(r'wd:Q(\d+)', query_text)
        for entity_id in entities:
            # Use LOGS_NS for entity references in this run
            entity_uri = self.LOGS_NS[f"WikidataEntity_Q{entity_id}"]
            self.graph.add((query_uri, self.LOG.referencesEntity, entity_uri))
            self.graph.add((entity_uri, RDF.type, self.LOG.WikidataEntity))
            self.graph.add((entity_uri, self.LOG.wikidataId, Literal(f"Q{entity_id}")))
        
        # Extract Wikidata properties (P numbers)
        properties = re.findall(r'wdt:P(\d+)', query_text)
        for prop_id in properties:
            # Use LOGS_NS for property references in this run
            prop_uri = self.LOGS_NS[f"WikidataProperty_P{prop_id}"]
            self.graph.add((query_uri, self.LOG.referencesProperty, prop_uri))
            self.graph.add((prop_uri, RDF.type, self.LOG.WikidataProperty))
            self.graph.add((prop_uri, self.LOG.wikidataId, Literal(f"P{prop_id}")))
    
    def _add_template_pattern(self, event_uri, template, event_id):
        """Add template pattern information"""
        import hashlib
        template_hash = hashlib.md5(template.encode()).hexdigest()[:8]
        
        # Use LXID for template pattern (shared vocabulary)
        if template not in self.templates:
            template_uri = self.LXID[f"LogEventTemplate_{template_hash}"]
            self.templates[template] = template_uri
            
            self.graph.add((template_uri, RDF.type, self.LOGEX.LogEventTemplate))
            self.graph.add((template_uri, self.LOGEX.pattern, Literal(template)))
            
            # Extract keywords from template
            keywords = self._extract_keywords(template)
            for keyword in keywords:
                self.graph.add((template_uri, self.LOGEX.keyword, Literal(keyword)))
        
        self.graph.add((event_uri, self.LOGEX.template, self.templates[template]))
    
    def _extract_keywords(self, template):
        """Extract keywords from template pattern"""
        # Remove parameter placeholders and extract meaningful words
        cleaned = re.sub(r'<\*>', '', template)
        words = cleaned.lower().split()
        # Filter out common words and short words
        keywords = [w for w in words if len(w) > 3 and w not in ['from', 'with', 'the', 'and', 'for']]
        return keywords
    
    def _add_parameters(self, event_uri, details, event_id):
        """Add parameter information"""
        parameters = []
        
        # Collect parameters from various detail keys
        if 'parameters' in details:
            parameters = details['parameters']
        
        # Look for property-related keys
        for key, value in details.items():
            if key.endswith('_properties') and isinstance(value, list):
                parameters.extend(value)
        
        # Add parameter list - use LOGS_NS for instance data
        if parameters:
            param_list_uri = self.LOGS_NS[f"ParamList_{event_id}"]
            self.graph.add((event_uri, self.LOG.hasParameterList, param_list_uri))
            
            for i, param in enumerate(parameters):
                param_uri = self.LOGS_NS[f"Param_{event_id}_{i}"]
                self.graph.add((param_list_uri, self.LOG.hasParameter, param_uri))
                self.graph.add((param_uri, self.LOG.position, Literal(i)))
                self.graph.add((param_uri, self.LOG.value, Literal(str(param))))
                
                # Determine parameter type
                param_type = self._determine_parameter_type(param)
                if param_type:
                    self.graph.add((param_uri, self.LOG.parameterType, Literal(param_type)))
    
    def _determine_parameter_type(self, param):
        """Determine parameter type based on content"""
        param_str = str(param)
        
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', param_str):
            return "ip"
        elif re.match(r'^\d{1,5}$', param_str) and 1 <= int(param_str) <= 65535:
            return "port"
        elif re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', param_str) and len(param_str) < 32:
            return "username"
        elif re.match(r'^https?://', param_str):
            return "url"
        elif re.match(r'^\d{4}-\d{2}-\d{2}', param_str):
            return "timestamp"
        else:
            return "unknown"
    
    def _add_results(self, event_uri, results, event_id):
        """Add query results"""
        if isinstance(results, list):
            # Use LOGS_NS for result set instance
            result_set_uri = self.LOGS_NS[f"ResultSet_{event_id}"]
            self.graph.add((event_uri, self.LOG.hasResultSet, result_set_uri))
            self.graph.add((result_set_uri, RDF.type, self.LOG.ResultSet))
            self.graph.add((result_set_uri, self.LOG.resultCount, Literal(len(results))))
            
            # Add individual results (limit to first 10 for performance)
            for i, result in enumerate(results[:10]):
                result_uri = self.LOGS_NS[f"Result_{event_id}_{i}"]
                self.graph.add((result_set_uri, self.LOG.hasResult, result_uri))
                self.graph.add((result_uri, RDF.type, self.LOG.QueryResult))
                
                if isinstance(result, dict):
                    for key, value in result.items():
                        prop = self.LOG[key]
                        self.graph.add((result_uri, prop, Literal(str(value))))
    
    def _add_generic_detail(self, event_uri, key, value, event_id):
        """Add generic detail as RDF triple"""
        # Create property name from key
        prop_name = f"has{key.replace('_', ' ').title().replace(' ', '')}"
        prop = self.LOG[prop_name]
        
        if isinstance(value, (str, int, float, bool)):
            self.graph.add((event_uri, prop, Literal(value)))
        elif isinstance(value, list) and len(value) > 0:
            # Create a collection for lists - use LOGS_NS for list instance
            list_uri = self.LOGS_NS[f"List_{event_id}_{key}"]
            self.graph.add((event_uri, prop, list_uri))
            
            for i, item in enumerate(value):
                item_uri = self.LOGS_NS[f"Item_{event_id}_{key}_{i}"]
                self.graph.add((list_uri, self.LOG.hasItem, item_uri))
                self.graph.add((item_uri, self.LOG.position, Literal(i)))
                self.graph.add((item_uri, self.LOG.value, Literal(str(item))))
    
    def convert_logs_to_rdf(self, logs):
        """Convert all logs to RDF"""
        for log_entry in logs:
            self.add_log_event(log_entry)
        
        # Add metadata about the log conversion
        self._add_metadata(logs)
    
    def _add_metadata(self, logs):
        """Add metadata about the log conversion process"""
        # Use run ID directly as the metadata entity
        self.graph.add((self.metadata_uri, RDF.type, self.LOGEX.ConversionMetadata))
        self.graph.add((self.metadata_uri, self.LOGEX.totalEvents, Literal(len(logs))))
        
        # Add this run to the global collection
        self.graph.add((self.all_runs_uri, self.LOGEX.hasRun, self.metadata_uri))
        
        # Extract start time and end time from logs
        start_time = None
        end_time = None
        
        for log in logs:
            timestamp_str = log.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
                if start_time is None or timestamp < start_time:
                    start_time = timestamp
                if end_time is None or timestamp > end_time:
                    end_time = timestamp
        
        # Add start time, end time, and total duration
        if start_time and end_time:
            self.graph.add((self.metadata_uri, self.LOGEX.startTime, Literal(start_time, datatype=XSD.dateTime)))
            self.graph.add((self.metadata_uri, self.LOGEX.endTime, Literal(end_time, datatype=XSD.dateTime)))
            duration = (end_time - start_time).total_seconds()
            self.graph.add((self.metadata_uri, self.LOGEX.totalDuration, Literal(duration, datatype=XSD.float)))
        
        # Count event types
        event_types = {}
        process_nodes = set()
        
        for log in logs:
            event_type = log.get('event_type', 'unknown')
            component = log.get('component', 'unknown')
            
            # Track event types
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Track process nodes
            process_nodes.add(component)
        
        # Add event type statistics
        for event_type, count in event_types.items():
            type_uri = self.LOGID[f"EventType_{event_type.replace(' ', '_')}"]
            self.graph.add((self.metadata_uri, self.LOGEX.hasEventType, type_uri))
            self.graph.add((type_uri, RDFS.label, Literal(event_type)))
            self.graph.add((type_uri, self.LOGEX.eventCount, Literal(count)))
            
        # Add node information
        for node in process_nodes:
            node_uri = self.LOGID[f"{node.replace(' ', '_')}_Node"]
            self.graph.add((self.metadata_uri, self.LOGEX.hasNode, node_uri))
            self.graph.add((node_uri, RDF.type, self.LOG.ProcessNode))
            self.graph.add((node_uri, RDFS.label, Literal(node)))
    
    def serialize_to_ttl(self):
        """Serialize the RDF graph to TTL format"""
        return self.graph.serialize(format='turtle')

class BoxologyVisualizer:
    """Visualizer for displaying detailed process flow of the WikidataGraphRAG execution as a diagram using Mermaid Markdown"""
    def __init__(self, verbose=1, debug_callback=None):
        self.logs = []
        self.verbose = verbose
        self.start_time = datetime.now()
        self.question = None  # Add this to store the question
        self.debug_callback = debug_callback
        
        # Initialize Jena uploader
        self.jena_uploader = JenaUploader()
        
        # Define color scheme based on boxology notation
        self.colors = {
            "Translation Node": "#d6efc7",           # Light green for transformation
            "Entity Extraction Node": "#bcd6e7",     # Light blue for data process
            "Strategy Selection Node": "#f6d5a7",    # Light orange for decision
            "Verbalization Node": "#e7d3f2",         # Light purple for generation
            "Property Generation Node": "#ffd5d5",   # Light red for property related
            "SPARQL Generation Node": "#d5f5f5",     # Light teal for query related
            "Answer Generation Node": "#f5f5d5",     # Light yellow for inference
            "default": "#f5f5f5"                     # Light gray for default
        }
        
        # Define shapes based on boxology notation
        self.shapes = {
            "Translation Node": "rounded",           # Rounded rectangle for transformation process
            "Entity Extraction Node": "rounded",     # Rounded rectangle for process
            "Strategy Selection Node": "diamond",    # Diamond for decision
            "Verbalization Node": "rounded",         # Rounded rectangle for generation
            "Property Generation Node": "rounded",   # Rounded rectangle for generation
            "SPARQL Generation Node": "rounded",     # Rounded rectangle for inference
            "Answer Generation Node": "rounded",     # Rounded rectangle for inference
            "default": "box"                         # Rectangle for default
        }
    
    def update_debug_callback(self, new_callback):
        """Update the debug callback function without recreating the visualizer"""
        self.debug_callback = new_callback
    
    def set_question(self, question):
        """Set the question for this visualization session"""
        self.question = question
    
    def log_event(self, component, event_type, details=None, start_time=None, end_time=None):
        """Log a process event with timestamp"""
        if self.verbose < 1:
            return
            
        timestamp = datetime.now()
        log_entry = {
            "component": component,
            "event_type": event_type,
            "details": details,
            "timestamp": timestamp.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        }
        
        self.logs.append(log_entry)
        
        # If debug_callback is provided, send the log entry through it
        if self.debug_callback:
            debug_msg = f"{component} - {event_type}"
            if details:
                debug_msg += f"\nDetails: {json.dumps(details, cls=CustomEncoder, indent=2)}"
            
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                debug_msg += f"\nDuration: {duration:.3f}s"
            
            # self.debug_callback(debug_msg)
            if asyncio.iscoroutinefunction(self.debug_callback):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(self.debug_callback(debug_msg), loop)
                        # Optionally wait for result with timeout
                        try:
                            future.result(timeout=1.0)
                        except Exception as e:
                            print(f"Error in async callback: {e}")
                    else:
                        loop.run_until_complete(self.debug_callback(debug_msg))
                except RuntimeError:
                    # No event loop in this thread, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.debug_callback(debug_msg))
            else:
                # Regular synchronous callback
                try:
                    self.debug_callback(debug_msg)
                except Exception as e:
                    print(f"Error in callback: {e}")
    
    def _get_filename_base(self):
        """Generate the base filename from datetime and question"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Clean the question for filename
        if self.question:
            # Remove special characters and truncate
            clean_question = re.sub(r'[^\w\s-]', '', self.question).strip()
            clean_question = re.sub(r'[-\s]+', '_', clean_question)[:50]
            return f"{timestamp}_{clean_question}"
        else:
            return f"{timestamp}_unknown_question"
    
    def save_logs_to_json(self):
        """Save logs to a JSON file with datetime and question in filename"""
        if not self.logs:
            return None
        
        # Prepare data for saving
        log_data = {
            "question": self.question,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration": (datetime.now() - self.start_time).total_seconds(),
            "logs": self.logs
        }
        
        # Create a temp file and save the JSON data
        temp_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        with open(temp_file.name, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False, cls=CustomEncoder)
        
        if self.verbose > 0:
            print(f"Logs saved to: {temp_file.name}")
        
        return temp_file.name
    
    def sanitize_for_mermaid(self, text):
        """Sanitize text for safe inclusion in Mermaid diagram nodes using backticks for special characters"""
        if text is None:
            return ""
        
        # Handle numpy types
        if isinstance(text, (np.float32, np.float64)):
            text = float(text)
        elif isinstance(text, (np.int32, np.int64)):
            text = int(text)
        elif isinstance(text, np.ndarray):
            text = text.tolist()
        
        # Handle double quotes and backslashes
        text = str(text).replace('"', "'")
        
        # Remove backticks to avoid Mermaid parsing issues
        text = text.replace('`', '')
        
        # Escape special characters
        text = text.replace('>', '&gt;')
        text = text.replace('<', '&lt;')
        
        # Truncate if too long
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text
    
    def format_nested_structure(self, data, indent_level=0):
        """Format nested dictionaries and lists for display in a single box"""
        if data is None:
            return "None"
        
        indent = "  " * indent_level
        
        if isinstance(data, dict):
            if not data:
                return "{}"
            
            lines = []
            for key, value in data.items():
                key_str = self.sanitize_for_mermaid(str(key))
                if isinstance(value, (dict, list)):
                    value_str = self.format_nested_structure(value, indent_level + 1)
                    lines.append(f"{indent}{key_str}:")
                    lines.append(value_str)
                else:
                    value_str = self.sanitize_for_mermaid(str(value))
                    lines.append(f"{indent}{key_str}: {value_str}")
            
            return "\n".join(lines)
        
        elif isinstance(data, list):
            if not data:
                return "[]"
            
            lines = []
            for item in data:
                if isinstance(item, (dict, list)):
                    item_str = self.format_nested_structure(item, indent_level + 1)
                    lines.append(f"{indent}•")
                    lines.append(item_str)
                else:
                    item_str = self.sanitize_for_mermaid(str(item))
                    lines.append(f"{indent}• {item_str}")
            
            return "\n".join(lines)
        
        else:
            return indent + self.sanitize_for_mermaid(str(data))
    
    def save_mermaid_diagram(self):
        """Generate and save the mermaid diagram to a file"""
        if not self.logs:
            return None
            
        # Create Mermaid diagram code
        mermaid_code = ["graph LR;"]
        
        # Add title
        mermaid_code.append("    title[\"WikidataGraphRAG Process Flow\"]")
        mermaid_code.append("    style title fill:#f9f9f9,stroke:#333,stroke-width:2px,font-size:16px,font-weight:bold,color:#444")
        
        # Group logs by component
        components = {}
        for log in self.logs:
            comp = log["component"]
            if comp not in components:
                components[comp] = []
            components[comp].append(log)
        
        # Node counter for unique IDs
        node_counter = {'count': 0}
        
        # Create subgraphs for each component with proper background color
        components_list = list(components.keys())
        
        for comp_name in components:
            node_id = re.sub(r'\s+', '', comp_name)
            shape = self.shapes.get(comp_name, self.shapes["default"])
            color = self.colors.get(comp_name, self.colors["default"])
            
            # Create subgraph with background color
            mermaid_code.append(f"    subgraph {node_id}_subgraph [\"{comp_name}`\"]")
            mermaid_code.append(f"        style {node_id}_subgraph fill:{color},stroke:#333,stroke-width:3px,font-weight:bold,color:#444")
            
            # Sort logs by timestamp
            events = sorted(components[comp_name], key=lambda x: x["timestamp"])
            
            # Add event nodes
            for i, event in enumerate(events):
                event_id = f"{node_id}_event_{i}"
                event_type = event["event_type"]
                
                # Events show as notes
                if event_type in ["start", "end"]:
                    event_text = f"{event_type.capitalize()} at {datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S.%f')[:-3]}"
                    if event_type == "end" and event["start_time"] and event["end_time"]:
                        start_dt = datetime.fromisoformat(event["start_time"])
                        end_dt = datetime.fromisoformat(event["end_time"])
                        duration = (end_dt - start_dt).total_seconds()
                        event_text += f" (Duration: {duration:.3f}s)"
                    mermaid_code.append(f"        {event_id}[\"{event_text}\"]")
                    mermaid_code.append(f"        style {event_id} fill:#f0f0f0,stroke:#666,stroke-width:2px,stroke-dasharray: 5 5,color:#444")
                else:
                    # Other event types
                    mermaid_code.append(f"        {event_id}[\"{event_type} at {datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S.%f')[:-3]}\"]")
                    mermaid_code.append(f"        style {event_id} fill:white,stroke:#444,stroke-width:2px,color:#444")
                
                # Add details if available
                if event["details"]:
                    detail_id = f"{event_id}_details"
                    
                    # Format the details for display in a single box
                    if isinstance(event["details"], (dict, list)):
                        # Format nested structures nicely
                        detail_text = self.format_nested_structure(event["details"])
                    else:
                        # Simple value details
                        detail_text = self.sanitize_for_mermaid(str(event["details"]))
                    
                    # Create a single box with the formatted content
                    mermaid_code.append(f"        {detail_id}[\"`{detail_text}`\"]")
                    mermaid_code.append(f"        style {detail_id} fill:#f9f9f9,stroke:#aaa,stroke-width:1px,font-size:12px,text-align:left,color:#444")
                    mermaid_code.append(f"        {event_id} -->|\"details\"| {detail_id}")
                    # Make the detail arrow black
                    mermaid_code.append(f"        linkStyle {node_counter['count']} stroke:#000,stroke-width:1px,fill:none")
                    node_counter['count'] += 1
                
                # Connect events in sequence
                if i > 0:
                    prev_event_id = f"{node_id}_event_{i-1}"
                    mermaid_code.append(f"        {prev_event_id} --> {event_id}")
                    # Make the event sequence arrow black
                    mermaid_code.append(f"        linkStyle {node_counter['count']} stroke:#000,stroke-width:2px,fill:none")
                    node_counter['count'] += 1
            
            mermaid_code.append("    end")
        
        # Force vertical alignment between subgraphs
        for i in range(len(components_list) - 1):
            current = re.sub(r'\s+', '', components_list[i])
            next_comp = re.sub(r'\s+', '', components_list[i+1])
            
            # Add invisible connection to force vertical layout
            mermaid_code.append(f"    {current}_subgraph --> {next_comp}_subgraph")
            mermaid_code.append(f"    linkStyle {node_counter['count']} stroke:transparent,stroke-width:0px")
            node_counter['count'] += 1
        
        # Create connections between subgraphs based on execution flow
        for i in range(len(components_list) - 1):
            current = re.sub(r'\s+', '', components_list[i])
            next_comp = re.sub(r'\s+', '', components_list[i+1])
            
            # Get the last event from current component and first event from next component
            current_events = sorted(components[components_list[i]], key=lambda x: x["timestamp"])
            next_events = sorted(components[components_list[i+1]], key=lambda x: x["timestamp"])
            
            if current_events and next_events:
                last_event_id = f"{current}_event_{len(current_events)-1}"
                first_event_id = f"{next_comp}_event_0"
                
                # Add arrow between subgraphs with neon yellow color
                mermaid_code.append(f"    {last_event_id} ==>|\"output\"| {first_event_id}")
                mermaid_code.append(f"    linkStyle {node_counter['count']} stroke:#FFFF00,stroke-width:4px,fill:none")
                node_counter['count'] += 1
        
        # Add overall execution info
        total_duration = (datetime.now() - self.start_time).total_seconds()
        mermaid_code.append(f"    executionInfo[\"Total Duration: {total_duration:.3f} seconds\"]")
        mermaid_code.append(f"    style executionInfo fill:#e8f7e8,stroke:#191,stroke-width:2px,font-weight:bold,color:#444")
        mermaid_code.append(f"    title --> executionInfo")
        mermaid_code.append(f"    linkStyle {node_counter['count']} stroke:#000,stroke-width:2px,fill:none")
            
        # Convert to Mermaid diagram markdown
        mermaid_diagram = "\n".join(mermaid_code)
        
        # Create a temp file and save the Mermaid markdown
        temp_file = tempfile.NamedTemporaryFile(suffix='.mmd', delete=False)
        
        # Create markdown content with mermaid code
        markdown_content = f"""# WikidataGraphRAG Process Flow

Question: {self.question}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

```mermaid
{mermaid_diagram}
```
"""
        
        with open(temp_file.name, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        if self.verbose > 0:
            print(f"Mermaid diagram saved to: {temp_file.name}")
        
        return temp_file.name

    def save_ttl(self):
        """Convert logs to RDF and save as TTL file locally and to Apache Jena"""
        # Create a converter with run ID
        import hashlib
        
        # Generate a consistent ID based on question and timestamp
        question_hash = hashlib.md5(str(self.question).encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        run_id = f"run_{timestamp}_{question_hash}"
        
        converter = LogToRDF(run_id=run_id)
        converter.convert_logs_to_rdf(self.logs)
        
        # Serialize to TTL
        ttl_content = converter.serialize_to_ttl()
        
        # Create a temp file and save the TTL content locally
        temp_file = tempfile.NamedTemporaryFile(suffix='.ttl', delete=False)
        with open(temp_file.name, 'w', encoding='utf-8') as f:
            f.write(ttl_content)
        
        if self.verbose > 0:
            print(f"TTL saved to: {temp_file.name}")
        
        # Upload to Apache Jena
        try:
            # Create graph name using run ID
            graph_name = f"http://example.org/logs/{run_id}"
            
            # Upload to Apache Jena
            upload_success = self.jena_uploader.upload_ttl(ttl_content, graph_name)
            
            if upload_success:
                logger.info(f"Successfully uploaded TTL data to Apache Jena with graph: {graph_name}")
            else:
                logger.error("Failed to upload TTL data to Apache Jena")
        except Exception as e:
            logger.error(f"Error uploading TTL data to Apache Jena: {e}")
        
        return temp_file.name
    
    def save_visualization_files(self):
        """Generate visualization data (mermaid diagram, TTL file) and return file paths"""
        if self.verbose < 1 or not self.logs:
            return None
            
        # Save files
        json_path = self.save_logs_to_json()
        mermaid_path = self.save_mermaid_diagram()
        ttl_path = self.save_ttl()
        
        return {
            "json_path": json_path,
            "mermaid_path": mermaid_path,
            "ttl_path": ttl_path,
        }