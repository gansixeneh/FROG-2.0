"""
Schema Manager for Knowledge Graph Extraction

This utility manages the extraction and caching of knowledge graph schemas,
preventing redundant processing of the same RDF data.
"""

import os
import pickle
import json
import time
from datetime import datetime


class SchemaManager:
    """
    Manages knowledge graph schema extraction and caching.
    """
    
    def __init__(self, cache_dir='schema_cache', use_cache=True):
        """
        Initialize the Schema Manager.
        
        Args:
            cache_dir (str): Directory to store cached schema files
            use_cache (bool): Whether to use cached schemas when available
        """
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def get_schema(self, source_file, extractor_class, extractor_options=None, force_reextract=False):
        """
        Get schema for an RDF source, using cache if available.
        
        Args:
            source_file (str): Path to the RDF file
            extractor_class: The class to use for extraction (e.g., KGSchemaExtractor)
            extractor_options (dict): Options to pass to the extractor
            force_reextract (bool): If True, ignore cache and re-extract
            
        Returns:
            dict: The extracted schema
        """
        # Generate cache filename based on source file and modification time
        file_mtime = os.path.getmtime(source_file)
        file_hash = f"{source_file}_{file_mtime}"
        cache_filename = os.path.join(self.cache_dir, 
                                      f"{os.path.basename(source_file)}.{hash(file_hash)}.pkl")
        
        # Check if cache should be used
        if self.use_cache and not force_reextract and os.path.exists(cache_filename):
            print(f"Loading schema from cache: {cache_filename}")
            try:
                with open(cache_filename, 'rb') as f:
                    schema = pickle.load(f)
                
                # Create and store cache metadata for reference
                self._update_metadata(cache_filename, source_file, "loaded")
                
                return schema
            except Exception as e:
                print(f"Error loading cached schema: {e}")
                print("Will re-extract schema")
        
        # Extract schema if no cache or cache shouldn't be used
        print(f"Extracting schema from {source_file}")
        start_time = time.time()
        
        # Create extractor instance and extract schema
        extractor = extractor_class(extractor_options or {})
        schema = extractor.extract_from_file(source_file, format=self._guess_format(source_file))
        
        extraction_time = time.time() - start_time
        
        # Save schema to cache
        if self.use_cache:
            try:
                with open(cache_filename, 'wb') as f:
                    pickle.dump(schema, f)
                print(f"Schema cached to: {cache_filename}")
                
                # Store metadata about this extraction
                self._update_metadata(cache_filename, source_file, "extracted", extraction_time)
                
            except Exception as e:
                print(f"Warning: Failed to cache schema: {e}")
        
        return schema
    
    def clear_cache(self, older_than=None):
        """
        Clear cached schema files.
        
        Args:
            older_than (int): If provided, only clear files older than this many days
        """
        files_deleted = 0
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl'):
                file_path = os.path.join(self.cache_dir, filename)
                
                # Check age if needed
                if older_than:
                    file_age_days = (time.time() - os.path.getmtime(file_path)) / (86400)
                    if file_age_days < older_than:
                        continue
                
                # Delete the file
                try:
                    os.remove(file_path)
                    files_deleted += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        print(f"Cleared {files_deleted} cached schema files")
    
    def list_cached_schemas(self):
        """List all cached schemas with their metadata."""
        cached_files = []
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl'):
                file_path = os.path.join(self.cache_dir, filename)
                meta_path = file_path + '.meta.json'
                
                # Get basic file info
                file_info = {
                    'filename': filename,
                    'size': os.path.getsize(file_path),
                    'created': datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add metadata if available
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r') as f:
                            metadata = json.load(f)
                        file_info.update(metadata)
                    except:
                        file_info['metadata_error'] = "Failed to load metadata"
                
                cached_files.append(file_info)
        
        return cached_files
    
    def _update_metadata(self, cache_filename, source_file, action, extraction_time=None):
        """
        Update metadata for a cached schema file.
        
        Args:
            cache_filename (str): Path to the cached schema file
            source_file (str): Original RDF file path
            action (str): Action performed ("loaded" or "extracted")
            extraction_time (float): Time taken for extraction, if applicable
        """
        meta_filename = cache_filename + '.meta.json'
        
        metadata = {
            'source_file': source_file,
            'source_size': os.path.getsize(source_file),
            'source_modified': datetime.fromtimestamp(os.path.getmtime(source_file)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_action': action,
            'last_action_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if extraction_time:
            metadata['extraction_time_seconds'] = extraction_time
        
        try:
            with open(meta_filename, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save schema metadata: {e}")
    
    def _guess_format(self, filename):
        """
        Guess the RDF format based on file extension.
        
        Args:
            filename (str): Path to RDF file
            
        Returns:
            str: Format name for rdflib
        """
        ext = os.path.splitext(filename)[1].lower()
        
        formats = {
            '.ttl': 'turtle',
            '.nt': 'nt',
            '.nq': 'nquads',
            '.rdf': 'xml',
            '.owl': 'xml',
            '.xml': 'xml',
            '.n3': 'n3',
            '.jsonld': 'json-ld'
        }
        
        return formats.get(ext, 'turtle')  # Default to turtle


# Example usage
if __name__ == "__main__":
    # This would be imported in your actual code
    from kg_schema_extractor import KGSchemaExtractor
    
    # Initialize schema manager
    manager = SchemaManager()
    
    # Get schema (will be extracted first time, loaded from cache afterwards)
    schema = manager.get_schema('final_result.ttl', KGSchemaExtractor, {"debug": True})
    
    # Display some information about the schema
    print(f"Schema contains {len(schema['schemaInfo']['types'])} types and "
          f"{len(schema['schemaInfo']['properties'])} properties")
    
    # List cached schemas
    cached = manager.list_cached_schemas()
    print(f"\nCached schemas: {len(cached)}")
    for item in cached:
        print(f"- {item['filename']} ({item.get('source_file', 'unknown')})")