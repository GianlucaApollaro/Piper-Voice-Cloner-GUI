
import os
from collections import Counter

metadata_file = r"J:\piper_ui\Datasets\Ivo\metadata.csv"

def check_duplicates():
    if not os.path.exists(metadata_file):
        print(f"Error: File not found: {metadata_file}")
        return

    texts = []
    ids = []
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '|' in line:
                    parts = line.split('|', 1)
                    ids.append(parts[0])
                    texts.append(parts[1])

        # Check for duplicate IDs (Technical issue)
        id_counts = Counter(ids)
        dup_ids = {k: v for k, v in id_counts.items() if v > 1}
        
        # Check for duplicate Texts (User request - preserved features)
        text_counts = Counter(texts)
        dup_texts = {k: v for k, v in text_counts.items() if v > 1}


        with open(r"J:\piper_ui\final_report.txt", "w", encoding="utf-8") as out:
            out.write(f"Total Lines: {len(ids)}\n")
            out.write(f"Unique IDs: {len(id_counts)}\n")
            out.write(f"Unique Texts: {len(text_counts)}\n")
            
            if dup_texts:
                out.write(f"\nCONFIRMED: Found {len(dup_texts)} phrases that are repeated multiple times (Total repeated instances: {sum(dup_texts.values()) - len(dup_texts)}).\n")
                out.write("Examples of repeated phrases:\n")
                for text, count in list(dup_texts.items())[:10]:
                    out.write(f"- '{text}' appears {count} times\n")
            else:
                out.write("\nWarning: No repeated phrases found.\n")

    except Exception as e:
        print(f"Error processing metadata: {e}")

if __name__ == "__main__":
    check_duplicates()
