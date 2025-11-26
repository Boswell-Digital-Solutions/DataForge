#!/usr/bin/env python3
"""
Script to fix absolute imports to relative imports in neuroforge_backend
"""
import os
import re
from pathlib import Path

# Mapping of absolute import patterns to relative import replacements
# Key: regex pattern, Value: replacement string
IMPORT_FIXES = {
    # Top-level modules that should be relative imports
    r'^from repositories\.': 'from ..repositories.',
    r'^from models\.': 'from ..models.',
    r'^from database\.': 'from ..database.',
    r'^from adapters\.': 'from ..adapters.',
    r'^from utils\.': 'from ..utils.',
    r'^from services\.': 'from ..services.',
    r'^from routers\.': 'from ..routers.',
    r'^from config import': 'from ..config import',
    r'^from auth import': 'from ..auth import',
    r'^from auth_router import': 'from ..auth_router import',
    r'^from rag\.': 'from ..rag.',
    r'^from monitoring\.': 'from ..monitoring.',
    r'^from workbench\.': 'from ..workbench.',
}

def fix_imports_in_file(file_path):
    """Fix imports in a single file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original = content
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            fixed_line = line
            for pattern, replacement in IMPORT_FIXES.items():
                # Only fix lines that are actual imports
                if re.match(r'^\s*(from|import)\s+', line):
                    fixed_line = re.sub(pattern, replacement, fixed_line)
            fixed_lines.append(fixed_line)
        
        content = '\n'.join(fixed_lines)
        
        if content != original:
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def fix_all_imports(base_dir):
    """Fix imports in all Python files in the directory"""
    base_path = Path(base_dir)
    modified_files = []
    
    # Skip certain directories
    skip_dirs = {'.venv', 'venv', '__pycache__', '.git', '.pytest_cache', 'target'}
    
    for py_file in base_path.rglob('*.py'):
        # Skip if in excluded directory
        if any(skip_dir in py_file.parts for skip_dir in skip_dirs):
            continue
        
        # Skip main.py in the root since it should have relative imports
        if py_file.name in ['__init__.py'] and py_file.parent == base_path:
            continue
            
        if fix_imports_in_file(py_file):
            modified_files.append(py_file)
            print(f"Fixed: {py_file.relative_to(base_path)}")
    
    return modified_files

if __name__ == '__main__':
    backend_dir = Path(__file__).parent / 'neuroforge_backend'
    print(f"Fixing imports in: {backend_dir}")
    print("=" * 60)
    
    modified = fix_all_imports(backend_dir)
    
    print("=" * 60)
    print(f"Modified {len(modified)} files")
