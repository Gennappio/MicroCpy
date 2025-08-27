import os
import re

def remove_special_characters(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove emojis and other special characters
        cleaned_content = re.sub(r'[^\x00-\x7F]+', '', content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
            
        print(f"Cleaned: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    src_dir = 'src'
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                remove_special_characters(file_path)

if __name__ == "__main__":
    main() 