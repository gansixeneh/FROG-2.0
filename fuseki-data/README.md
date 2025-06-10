# FrOG Apache Jena Fuseki Configuration

This directory contains configuration files and scripts for setting up Apache Jena Fuseki as the SPARQL endpoint for the FrOG (Framework of Open GraphRAG) system.

## Overview

Apache Jena Fuseki serves as the backend SPARQL server for our knowledge graphs. It hosts multiple RDF datasets that power the GraphRAG capabilities of the FrOG system.

## Datasets

The Fuseki server is configured with the following datasets:

-**curi**: Curriculum knowledge graph

-**modified-lex2kg**: Modified Indonesian legal document knowledge graph

-**gesis**: Modified GESIS scholarly articles knowledge graph

-**visualization-logs**: Stores execution logs of the agent in RDF format, enabling powerful semantic querying of agent execution patterns

## Setup Instructions

1. Ensure you have Apache Jena Fuseki installed on your system
2. Clone this repository
3. Navigate to the `fuseki-data` directory
4. Make the scripts executable:

```bash

chmod +x start_apache_jena.sh create_config.sh

```

5. Run the start script:

```bash

./start_apache_jena.sh

```

This will:

- Create the necessary configuration file (`config.ttl`)
- Create required directories if they don't exist
- Start the Fuseki server on port 3030

You can then access the Fuseki server at [http://localhost:3030](http://localhost:3030).

## Files

-`config.ttl`: Main configuration file for Fuseki (automatically generated)

-`create_config.sh`: Script to generate the Fuseki configuration

-`start_apache_jena.sh`: Script to start the Fuseki server

-`.gitignore`: Ignores data directories that store TDB files

## Using the Visualization Logs

The visualization logs dataset contains RDF data that tracks how the FrOG agent processes questions. You can use SPARQL queries to analyze:

- Query patterns and approaches
- Entity recognition
- Performance metrics
- Success rates
- User interaction patterns

Sample SPARQL queries for analyzing the logs are available in the frontend's JenaLogsModal component.

## Customization

If you need to add new datasets or modify the configuration:

1. Edit the `create_config.sh` script
2. Run the script to regenerate the configuration:

```bash

./create_config.sh

```

3. Restart Fuseki using `./start_apache_jena.sh`
