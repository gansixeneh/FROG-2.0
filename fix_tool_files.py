import os
import re

# Directory containing the tool files
tools_dir = 'tools'

# Process each Python file in the tools directory
for filename in os.listdir(tools_dir):
    if filename.endswith('.py') and filename != '__init__.py':
        filepath = os.path.join(tools_dir, filename)
        
        with open(filepath, 'r') as file:
            content = file.read()
        
        # Add ClassVar to the imports if needed
        if 'ClassVar' not in content:
            # If there's an existing import from typing, add ClassVar to it
            if 'from typing import' in content:
                content = re.sub(
                    r'from typing import (.*)',
                    r'from typing import \1, ClassVar',
                    content
                )
            else:
                # If no typing import exists, add it at the top after other imports
                content = re.sub(
                    r'(from .* import .*\n|import .*\n)(?!from|import)',
                    r'\1\nfrom typing import ClassVar\n',
                    content,
                    count=1
                )
        
        # Fix the tool class attributes
        # First, try to find the tool class
        tool_class_match = re.search(r'class (\w+)\(WikidataBaseTool\):', content)
        if tool_class_match:
            # Look for name and description attributes
            name_match = re.search(r'(\s+)name = "(.*?)"', content)
            desc_match = re.search(r'(\s+)description = "(.*?)"', content)
            
            # Replace with properly annotated versions
            if name_match:
                content = content.replace(
                    name_match.group(0),
                    f"{name_match.group(1)}name: ClassVar[str] = \"{name_match.group(2)}\""
                )
            
            if desc_match:
                content = content.replace(
                    desc_match.group(0),
                    f"{desc_match.group(1)}description: ClassVar[str] = \"{desc_match.group(2)}\""
                )
        
        # Write the modified content back
        with open(filepath, 'w') as file:
            file.write(content)
        
        print(f"Updated {filename}")

print("All tool files have been updated!")