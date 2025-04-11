import os
import re

# List all tool files
tool_files = [f for f in os.listdir('tools') if f.endswith('.py') and f != '__init__.py' and f != 'base.py']

for file in tool_files:
    file_path = os.path.join('tools', file)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace the name and description declarations with proper annotations
    content = re.sub(
        r'name = "([^"]+)"', 
        r'name: ClassVar[str] = "\1"', 
        content
    )
    
    content = re.sub(
        r'description = "([^"]+)"', 
        r'description: ClassVar[str] = "\1"', 
        content
    )
    
    # Add the ClassVar import if it's not already there
    if 'ClassVar' not in content:
        content = re.sub(
            r'from typing import (.*)',
            r'from typing import \1, ClassVar',
            content
        )
    
    with open(file_path, 'w') as f:
        f.write(content)

print("Updated all tool files!")