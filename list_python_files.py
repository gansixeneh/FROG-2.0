import os

def list_python_files_with_contents(directory='.', output_file='python_files_list.txt'):
    """
    Lists all Python files in the specified directory and its subdirectories,
    along with their contents, and saves to a text file with clear file separators.
    
    Args:
        directory (str): The directory to search for Python files. Defaults to current directory.
        output_file (str): Path to the output text file.
    """
    # Open the output file
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # Walk through the directory tree
        for root, dirs, files in os.walk(directory):
            # Find Python files
            for file in files:
                if file.endswith('.py'):
                    # Create the relative path
                    file_path = os.path.join(root, file)
                    
                    # Remove leading './' if present
                    if file_path.startswith('./'):
                        file_path = file_path[2:]
                    
                    # Write a clear file separator with the file path
                    out_f.write(f"{'=' * 80}\n")
                    out_f.write(f"FILE: {file_path}\n")
                    out_f.write(f"{'=' * 80}\n\n")
                    
                    # Read and write the file contents
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            out_f.write(f.read())
                    except Exception as e:
                        out_f.write(f"Error reading file: {e}\n")
                    
                    # Add space between files
                    out_f.write("\n\n")
    
    print(f"Output has been saved to {output_file}")

if __name__ == "__main__":
    # You can specify a directory and output file as command-line arguments
    import sys
    dir_to_search = sys.argv[1] if len(sys.argv) > 1 else '.'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'python_files_list.txt'
    
    list_python_files_with_contents(dir_to_search, output_file)