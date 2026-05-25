
import os
import csv

wavs_dir = r"J:\piper_ui\Datasets\Ivo\wavs"
metadata_file = r"J:\piper_ui\Datasets\Ivo\metadata.csv"

def check_coverage():

    output_file = r"J:\piper_ui\coverage_report.txt"
    
    with open(output_file, "w", encoding="utf-8") as out:
        # 1. Get all wav filenames (without extension)
        if not os.path.exists(wavs_dir):
            out.write(f"Error: Directory not found: {wavs_dir}\n")
            return

        wav_files = set()
        for f in os.listdir(wavs_dir):
            if f.lower().endswith(".wav"):
                wav_files.add(os.path.splitext(f)[0])
        
        out.write(f"Total WAV files found: {len(wav_files)}\n")

        # 2. Get all IDs from metadata.csv
        if not os.path.exists(metadata_file):
            out.write(f"Error: File not found: {metadata_file}\n")
            return

        metadata_ids = set()
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '|' in line:
                        parts = line.split('|')
                        metadata_ids.add(parts[0].strip())
        except Exception as e:
            out.write(f"Error reading metadata: {e}\n")
            return

        out.write(f"Total Metadata entries found: {len(metadata_ids)}\n")

        # 3. Find mismatches (Wavs present but not in metadata)
        orphaned_wavs = wav_files - metadata_ids
        
        if orphaned_wavs:
            out.write(f"\nFound {len(orphaned_wavs)} WAV files without metadata entries:\n")
            for wav in sorted(orphaned_wavs):
                out.write(f"- {wav}.wav\n")
        else:
            out.write("\nAll WAV files have corresponding metadata entries.\n")

        # Optional: check the reverse
        missing_wavs = metadata_ids - wav_files
        if missing_wavs:
            out.write(f"\nFound {len(missing_wavs)} Metadata entries without WAV files (should be 0 if cleaned):\n")
            for mid in sorted(missing_wavs):
                out.write(f"- {mid}\n")

if __name__ == "__main__":
    check_coverage()
