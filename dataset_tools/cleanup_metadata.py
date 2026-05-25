import os
import shutil

dataset_dir = r"J:\piper_ui\Datasets\Ivo"
metadata_path = os.path.join(dataset_dir, "metadata.csv")
wavs_dir = os.path.join(dataset_dir, "wavs")

if not os.path.exists(metadata_path):
    print(f"Error: {metadata_path} not found.")
    exit(1)

# Backup
backup_path = metadata_path + ".bak_cleanup"
shutil.copy(metadata_path, backup_path)
print(f"Backup created at {backup_path}")

new_lines = []
removed_count = 0

with open(metadata_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for line in lines:
    if "|" in line:
        file_id = line.split("|")[0].strip()
        wav_path = os.path.join(wavs_dir, f"{file_id}.wav")
        
        if os.path.exists(wav_path):
            new_lines.append(line)
        else:
            print(f"Removing: {file_id} (wav not found)")
            removed_count += 1
    else:
        # Keep empty or malformed lines? safer to skip or keep? 
        # Usually metadata is strict. Let's keep non-pipe lines just in case (comments/headers?) though piper doesn't use them.
        # But looking at the file it seems strict.
        pass

with open(metadata_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"Done. Removed {removed_count} lines. Metadata updated.")
