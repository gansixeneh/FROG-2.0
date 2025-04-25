# Dataset Directory

This directory contains test datasets for evaluating the Wikidata Query Agent.

## Directories

- `qald_9_plus/`: Contains the QALD-9-plus benchmark dataset with Wikidata SPARQL queries

## Expected File Structure

```
dataset/
└── qald_9_plus/
    └── qald_9_plus_test_wikidata.json
```

## Dataset Format

The test datasets should be in JSON format with the following structure:

```json
[
  {
    "question": "What is the time zone of Salt Lake City?",
    "sparql": "SELECT DISTINCT ?o1 WHERE { <http://www.wikidata.org/entity/Q23337> <http://www.wikidata.org/prop/direct/P421> ?o1 . }"
  },
  ...
]
```

Each entry contains:

- `question`: The natural language question
- `sparql`: The corresponding SPARQL query for Wikidata that answers the question

## Adding Custom Datasets

You can add your own test datasets in the same format. Make sure to update the path when running the evaluation:

```
python main.py --mode evaluate --test-data dataset/your_dataset/your_file.json
```
