#!/bin/bash

DATA_DIR="$(pwd)"

# Start the config.ttl file with prefix definitions
cat > config.ttl << 'EOF'
@prefix :      <#> .
@prefix fuseki: <http://jena.apache.org/fuseki#> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix tdb2:  <http://jena.apache.org/2016/tdb#> .
EOF

# Get the current user
current_user=$(whoami)

# Add visualization-logs dataset first
cat >> config.ttl << EOF

:service_visualization_logs  a          fuseki:Service ;
    rdfs:label                         "Visualization Logs Dataset" ;
    fuseki:dataset                     :dataset_visualization_logs ;
    fuseki:name                        "visualization-logs" ;
    fuseki:serviceQuery                "query" , "sparql" ;
    fuseki:serviceReadGraphStore       "get" ;
    fuseki:serviceReadWriteGraphStore  "data" ;
    fuseki:serviceUpdate               "update" ;
    fuseki:serviceUpload               "upload" .
:dataset_visualization_logs  a        tdb2:DatasetTDB2 ;
    tdb2:location      "$DATA_DIR/visualization-logs" ;
.
EOF

# Get all directories in the current folder
for dir in */; do
    # Skip if not a directory
    if [ ! -d "$dir" ]; then
        continue
    fi
    
    # Remove trailing slash
    dir_basename=${dir%/}
    
    # Skip if this is already the visualization-logs directory
    if [ "$dir_basename" = "visualization-logs" ]; then
        continue
    fi
    
    # Generate a human-readable label
    label=$(echo "$dir_basename" | sed 's/_/ /g' | sed 's/\b\(.\)/\u\1/g')
    label="$label Dataset"
    
    # Append service and dataset configuration for this directory
    cat >> config.ttl << EOF

:service_$dir_basename  a                   fuseki:Service ;
    rdfs:label                        "$label" ;
    fuseki:dataset                    :dataset_$dir_basename ;
    fuseki:name                       "$dir_basename" ;
    fuseki:serviceQuery               "query" , "sparql" ;
    fuseki:serviceReadGraphStore      "get" ;
    fuseki:serviceReadWriteGraphStore "data" ;
    fuseki:serviceUpdate              "update" ;
    fuseki:serviceUpload              "upload" .
:dataset_$dir_basename  a        tdb2:DatasetTDB2 ;
    tdb2:location      "$DATA_DIR/$dir_basename" ;
.
EOF
done

echo "Generated config.ttl with visualization-logs and other directories in the current folder."

# Create the visualization-logs directory if it doesn't exist
mkdir -p visualization-logs

# Optionally restart Fuseki server
echo "To start Fuseki server with this configuration, run:"
echo "fuseki-server --config=$DATA_DIR/config.ttl"