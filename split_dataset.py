import json
import random
from pathlib import Path

def split_dataset(folder_name, total_pairs=150, train_size=80, val_size=20, test_size=50):
    """
    Read dataset pairs from JSON file and split into train/val/test sets.
    
    Args:
        folder_name (str): Name of the folder containing the dataset
        total_pairs (int): Total number of pairs to select (default: 150)
        train_size (int): Number of pairs for training set (default: 80)
        val_size (int): Number of pairs for validation set (default: 20)
        test_size (int): Number of pairs for test set (default: 50)
    """
    
    # Verify that the split sizes add up to total_pairs
    if train_size + val_size + test_size != total_pairs:
        raise ValueError(f"Split sizes ({train_size} + {val_size} + {test_size} = {train_size + val_size + test_size}) don't match total_pairs ({total_pairs})")
    
    # Define file paths
    input_file = Path(folder_name) / "pattern_based_dataset_pair.json"
    train_file = Path(folder_name) / "train.json"
    val_file = Path(folder_name) / "val.json"
    test_file = Path(folder_name) / "test.json"
    
    # Create folder if it doesn't exist
    Path(folder_name).mkdir(parents=True, exist_ok=True)
    
    try:
        # Read the input JSON file
        print(f"Reading data from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Found {len(data)} pairs in the dataset")
        
        # Check if we have enough data
        if len(data) < total_pairs:
            print(f"Warning: Dataset has only {len(data)} pairs, but {total_pairs} requested.")
            print(f"Using all available {len(data)} pairs...")
            total_pairs = len(data)
            # Adjust split sizes proportionally
            ratio = len(data) / 150
            train_size = int(80 * ratio)
            val_size = int(20 * ratio)
            test_size = len(data) - train_size - val_size
            print(f"Adjusted split: train={train_size}, val={val_size}, test={test_size}")
        
        # Randomly sample the required number of pairs
        random.seed(42)  # For reproducibility
        selected_data = random.sample(data, total_pairs)
        
        # Split the data
        train_data = selected_data[:train_size]
        val_data = selected_data[train_size:train_size + val_size]
        test_data = selected_data[train_size + val_size:]
        
        # Save train set
        print(f"Saving {len(train_data)} pairs to {train_file}")
        with open(train_file, 'w', encoding='utf-8') as f:
            json.dump(train_data, f, indent=2, ensure_ascii=False)
        
        # Save validation set
        print(f"Saving {len(val_data)} pairs to {val_file}")
        with open(val_file, 'w', encoding='utf-8') as f:
            json.dump(val_data, f, indent=2, ensure_ascii=False)
        
        # Save test set
        print(f"Saving {len(test_data)} pairs to {test_file}")
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print("Dataset splitting completed successfully!")
        print(f"Split summary:")
        print(f"  Train: {len(train_data)} pairs")
        print(f"  Validation: {len(val_data)} pairs")
        print(f"  Test: {len(test_data)} pairs")
        print(f"  Total: {len(train_data) + len(val_data) + len(test_data)} pairs")
        
    except FileNotFoundError:
        print(f"Error: File {input_file} not found!")
        print("Please make sure the file exists and the path is correct.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {input_file}")
        print(f"JSON Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Usage example
if __name__ == "__main__":
    # Replace 'your_folder_name' with the actual folder name
    folder_name = "rw-curi"
    
    # Split the dataset
    split_dataset(folder_name)
    
    # Alternative usage with custom parameters:
    # split_dataset("my_dataset_folder", total_pairs=100, train_size=60, val_size=15, test_size=25)