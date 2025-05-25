#!/bin/bash
# Set the data directory to current working directory
DATA_DIR="$(pwd)"

# Check if the Fuseki configuration exists
if [ ! -f "$DATA_DIR/config.ttl" ]; then
    echo "Creating Fuseki configuration..."
    
    # Make sure the data directory exists
    mkdir -p "$DATA_DIR"
    
    # Change to the data directory
    cd "$DATA_DIR"
    
    # Run the configuration script
    bash create_config.sh
fi

# Create the visualization-logs directory if it doesn't exist
mkdir -p "$DATA_DIR/visualization-logs"

echo "Starting Apache Jena Fuseki server..."
echo "The server will be available at http://localhost:3030"

# Start the Fuseki server with the configuration
fuseki-server --config="$DATA_DIR/config.ttl"