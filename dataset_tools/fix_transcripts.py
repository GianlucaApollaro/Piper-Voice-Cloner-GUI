import os
import shutil

dataset_dir = r"J:\piper_ui\Datasets\Ivo"
metadata_path = os.path.join(dataset_dir, "metadata.csv")

if not os.path.exists(metadata_path):
    print(f"Error: {metadata_path} not found.")
    exit(1)

# Backup
shutil.copy(metadata_path, metadata_path + ".bak_punctuation")

replacements = {
    "caboli": "cavoli",
    "cabolfiori": "cavolfiori",
    "la ringa": "l'aringa",
    "piedina": "piadina",
    "manuca": "manuka",
    "diè.": "dieta.",
    "diè ": "dieta "
}

def fix_line(text):
    text = text.strip()
    if not text:
        return text
        
    # 1. Capitalize first letter
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
        
    # 2. Typos
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
        text = text.replace(wrong.capitalize(), right.capitalize())

    # 3. Final Punctuation
    # If ends with alphanumeric or comma, add/change to period.
    if text[-1].isalnum():
        text += "."
    elif text[-1] == ",":
        text = text[:-1] + "."
    elif text[-1] == ";":
        text = text[:-1] + "."
        
    return text

new_lines = []
with open(metadata_path, "r", encoding="utf-8") as f:
    for line in f:
        if "|" in line:
            parts = line.split("|", 1) # Split only on first |
            fid = parts[0]
            content = parts[1]
            
            new_content = fix_line(content)
            new_lines.append(f"{fid}|{new_content}\n")
        else:
            new_lines.append(line)

with open(metadata_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Transcriptions fixed.")
