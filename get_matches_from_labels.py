from typing import Literal
from search_wikidata_tool import SearchWikidataTool
from tqdm import tqdm
import json

searchWikidataTool = SearchWikidataTool()

def get_entity_property_matches(item_list, type: Literal["entity", "property"]):
    matches = {}
    for item in item_list:
        possible_uris = searchWikidataTool._run(item, type)
        matches[item] = possible_uris

    return matches

def process_questions(input_file: str):
    """
    Process questions from the input file, get entity and property matches, and save to output file.
    
    Args:
        input_file: Path to the input JSON file
    """
    # Load the input data
    with open(input_file, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)
    
    print(f"Processing {len(questions_data)} questions...")
    
    # Process each question
    processed_questions = []
    
    for question_item in tqdm(questions_data, desc="Processing questions", total=len(questions_data)):
        # Extract question, entities and properties
        question = question_item['question']
        entities = question_item['entities']
        properties = question_item['properties']
        
        # Get matches for entities and properties
        entities_matches = get_entity_property_matches(entities, "entity")
        # properties_matches = get_entity_property_matches(properties, "property")
        properties_matches = {}
        
        # Create new item with matches
        processed_item = {
            'question': question,
            'entities': entities,
            'properties': properties,
            'entities_matches': entities_matches,
            'properties_matches': properties_matches,
            'sparql': question_item.get('sparql', '')
        }
        
        processed_questions.append(processed_item)
    
    # Save results
    file_name = input_file.split("/")[-1].split(".")[0]
    output_file = f"dataset/possible_uris/{file_name}_possible_uris.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_questions, f, indent=2, ensure_ascii=False)
    
    print(f"Completed processing {len(processed_questions)} questions and saved to {output_file}")

if __name__ == "__main__":
    input_file = "dataset/labels/qald_9_plus_train_wikidata_converted_labels_finetune.json"
    
    process_questions(input_file)