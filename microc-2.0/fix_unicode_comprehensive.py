#!/usr/bin/env python3
"""
Comprehensive Unicode and Special Character Removal Script
Removes all Unicode characters, emojis, and special symbols from the entire project
to prevent cross-platform encoding issues.
"""

import os
import re
import sys
from pathlib import Path

# Unicode character mappings to ASCII equivalents
UNICODE_REPLACEMENTS = {
    # Checkmarks and crosses
    '[+]': '[+]',
    '[!]': '[!]',
    '[+]': '[+]',
    '[!]': '[!]',
    '[+]': '[+]',
    '[!]': '[!]',
    
    # Arrows
    '->': '->',
    '<-': '<-',
    '^': '^',
    'v': 'v',
    '=>': '=>',
    '<=': '<=',
    '^^': '^^',
    'vv': 'vv',
    '->': '->',
    '->': '->',
    
    # Bullets and symbols
    '*': '*',
    '-': '-',
    '*': '*',
    '-': '-',
    '*': '*',
    '-': '-',
    '*': '*',
    
    # Mathematical symbols
    'u': 'u',
    'alpha': 'alpha',
    'beta': 'beta',
    'gamma': 'gamma',
    'delta': 'delta',
    'epsilon': 'epsilon',
    'theta': 'theta',
    'lambda': 'lambda',
    'pi': 'pi',
    'sigma': 'sigma',
    'tau': 'tau',
    'phi': 'phi',
    'omega': 'omega',
    'Delta': 'Delta',
    'Sigma': 'Sigma',
    'Pi': 'Pi',
    'Omega': 'Omega',
    
    # Emojis and icons
    '[RUN]': '[RUN]',
    '[SAVE]': '[SAVE]',
    '[CHART]': '[CHART]',
    '[FOLDER]': '[FOLDER]',
    '[NOTE]': '[NOTE]',
    '[TOOL]': '[TOOL]',
    '[TARGET]': '[TARGET]',
    '[SUCCESS]': '[SUCCESS]',
    '[WARNING]': '[WARNING]',
    '[FAST]': '[FAST]',
    '[SEARCH]': '[SEARCH]',
    '[GRAPH]': '[GRAPH]',
    '[DECLINE]': '[DECLINE]',
    '[IDEA]': '[IDEA]',
    '[HOT]': '[HOT]',
    '[COLD]': '[COLD]',
    '[STAR]': '[STAR]',
    '[STAR]': '[STAR]',
    
    # Quotation marks
    '"': '"',
    '"': '"',
    '''''''''"': '"',
    '"': '"',
    
    # Dashes and hyphens
    '-': '-',
    '--': '--',
    '--': '--',
    '-': '-',
    '-': '-',
    
    # Spaces and separators
    ' ': ' ',  # Non-breaking space
    '': '',   # Zero-width space
    '': '',   # Zero-width non-joiner
    '': '',   # Zero-width joiner
    
    # Other common symbols
    '(c)': '(c)',
    '(R)': '(R)',
    '(TM)': '(TM)',
    'deg': 'deg',
    '+/-': '+/-',
    'x': 'x',
    '/': '/',
    '~=': '~=',
    '!=': '!=',
    '<=': '<=',
    '>=': '>=',
    'inf': 'inf',
    'sum': 'sum',
    'prod': 'prod',
    'integral': 'integral',
    'partial': 'partial',
    'nabla': 'nabla',
    'delta': 'delta',
    'sqrt': 'sqrt',
    'proportional': 'proportional',
    'in': 'in',
    'not_in': 'not_in',
    'union': 'union',
    'intersection': 'intersection',
    'subset': 'subset',
    'superset': 'superset',
    'subset_eq': 'subset_eq',
    'superset_eq': 'superset_eq',
}

def clean_unicode_text(text: str) -> str:
    """
    Clean Unicode characters from text using replacements and fallback removal
    
    Args:
        text: Input text with potential Unicode characters
        
    Returns:
        Cleaned ASCII text
    """
    # Apply specific replacements first
    for unicode_char, ascii_replacement in UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, ascii_replacement)
    
    # Remove any remaining non-ASCII characters
    # Keep only printable ASCII characters (32-126) plus common whitespace
    cleaned_text = ''
    for char in text:
        if ord(char) <= 127:  # ASCII range
            cleaned_text += char
        else:
            # Replace with placeholder or remove
            if char.isalpha():
                cleaned_text += '?'  # Placeholder for unknown letters
            # Skip other Unicode characters
    
    return cleaned_text

def should_process_file(file_path: Path) -> bool:
    """
    Determine if a file should be processed for Unicode removal
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file should be processed
    """
    # File extensions to process
    text_extensions = {
        '.py', '.md', '.txt', '.yaml', '.yml', '.json', '.csv', '.rst',
        '.cfg', '.ini', '.conf', '.log', '.bnd', '.toml'
    }
    
    # Skip binary files and certain directories
    skip_dirs = {
        '__pycache__', '.git', '.pytest_cache', 'node_modules',
        '.venv', 'venv', 'env', '.env', 'build', 'dist'
    }
    
    # Check if in skip directory
    for part in file_path.parts:
        if part in skip_dirs:
            return False
    
    # Check file extension
    return file_path.suffix.lower() in text_extensions

def process_file(file_path: Path) -> bool:
    """
    Process a single file to remove Unicode characters
    
    Args:
        file_path: Path to the file to process
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Read file with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        # Clean Unicode characters
        cleaned_content = clean_unicode_text(original_content)
        
        # Check if content changed
        if original_content != cleaned_content:
            # Write back with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(cleaned_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"[!] Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all files in the project"""
    
    print("[*] MicroC Unicode Cleanup Tool")
    print("=" * 50)
    print()
    
    # Get project root directory
    project_root = Path(__file__).parent
    
    # Statistics
    files_processed = 0
    files_modified = 0
    
    print(f"[*] Scanning project: {project_root}")
    print(f"[*] Looking for text files to clean...")
    print()
    
    # Walk through all files
    for file_path in project_root.rglob('*'):
        if file_path.is_file() and should_process_file(file_path):
            files_processed += 1
            
            # Show progress
            if files_processed % 10 == 0:
                print(f"[*] Processed {files_processed} files...")
            
            # Process file
            if process_file(file_path):
                files_modified += 1
                print(f"[+] Cleaned: {file_path.relative_to(project_root)}")
    
    print()
    print("=" * 50)
    print(f"[+] Unicode cleanup completed!")
    print(f"    Files processed: {files_processed}")
    print(f"    Files modified: {files_modified}")
    print(f"    Files unchanged: {files_processed - files_modified}")
    print()
    
    if files_modified > 0:
        print("[*] Summary of changes:")
        print("    * Unicode symbols replaced with ASCII equivalents")
        print("    * Emojis replaced with [BRACKET] notation")
        print("    * Mathematical symbols converted to text")
        print("    * Non-ASCII characters removed or replaced")
        print()
        print("[+] Project should now be free of Unicode encoding issues!")
    else:
        print("[+] No Unicode characters found - project already clean!")

if __name__ == "__main__":
    main()
