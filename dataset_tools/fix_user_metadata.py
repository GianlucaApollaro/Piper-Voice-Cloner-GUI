
import os

metadata_file = r"J:\piper_ui\Datasets\Ivo\metadata.csv"

def fix_metadata():
    if not os.path.exists(metadata_file):
        print(f"Error: File not found: {metadata_file}")
        return

    new_lines = []
    changes = 0
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if '|' in line:
                parts = line.split('|', 1)
                file_id = parts[0]
                text = parts[1]
                
                # Check for incorrect format (wavs/ prefix or .wav suffix)
                if file_id.startswith('wavs/') or file_id.endswith('.wav'):
                    changes += 1
                    # Strip wavs/
                    if file_id.startswith('wavs/'):
                        file_id = file_id[5:] # Remove 'wavs/'
                    
                    # Strip .wav
                    if file_id.lower().endswith('.wav'):
                        file_id = file_id[:-4]
                    
                    # Optional: Capitalize text if it's lowercase (standardize)
                    if text and text[0].islower():
                        text = text[0].upper() + text[1:]
                        
                    new_lines.append(f"{file_id}|{text}\n")
                else:
                    new_lines.append(line + "\n")
            else:
                new_lines.append(line + "\n")
        
        if changes > 0:
            print(f"Fixing {changes} entries...")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print("Done.")
        else:
            print("No incorrectly formatted entries found.")

    except Exception as e:
        print(f"Error processing metadata: {e}")

if __name__ == "__main__":
    fix_metadata()
