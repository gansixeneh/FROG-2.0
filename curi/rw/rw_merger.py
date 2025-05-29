import json

def merge_json_files():
    # Read the content from both files
    with open('curi_pattern_based.json', 'r') as file1:
        paste1_data = json.loads(file1.read())
    
    with open('curi_claude.json', 'r') as file2:
        paste2_data = json.loads(file2.read())
    
    # Create a dictionary from paste2 data for easy lookup by id
    paste2_dict = {item['id']: item for item in paste2_data}
    
    # Create a new list with updated items
    merged_data = []
    for item in paste1_data:
        # Check if this item exists in paste2
        if item['id'] in paste2_dict:
            # Update question and thoughts fields
            item['question'] = paste2_dict[item['id']]['question']
            item['thoughts'] = paste2_dict[item['id']]['thoughts']
        
        merged_data.append(item)
    
    # Write the merged data to a new file
    with open('curi_rw.json', 'w') as output_file:
        json.dump(merged_data, output_file, indent=2)
    
    print("Merged JSON file created")

if __name__ == "__main__":
    merge_json_files()