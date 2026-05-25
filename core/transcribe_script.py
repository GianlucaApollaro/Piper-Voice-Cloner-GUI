import os
import sys
import logging
from faster_whisper import WhisperModel

# This script is intended to run INSIDE a Docker container with GPU access
# Volume mounts: /data (contains 'split' folder with wavs)
# Output: /data/metadata.csv

def transcribe_folder(folder_path, model_size="large-v3", language="it"):
    print(f"Loading Whisper model: {model_size}...")
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
    except Exception as e:
        print(f"Error loading model on GPU, falling back to float32 or cpu: {e}")
        try:
            model = WhisperModel(model_size, device="cuda", compute_type="float32")
        except:
             model = WhisperModel(model_size, device="cpu", compute_type="int8")

    mp3_files = [f for f in os.listdir(folder_path) if f.endswith('.wav') or f.endswith('.mp3')]
    results = []

    print(f"Found {len(mp3_files)} files to transcribe.")
    
    for i, filename in enumerate(mp3_files):
        file_path = os.path.join(folder_path, filename)
        
        # Transcribe
        segments, info = model.transcribe(file_path, language=language, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        
        # Piper format: filename|text
        # Filename should be without extension? Usually yes.
        file_id = os.path.splitext(filename)[0]
        
        # Clean text: remove newlines
        text = text.replace('\n', ' ')
        
        if text:
            line = f"{file_id}|{text}"
            results.append(line)
            print(f"[{i+1}/{len(mp3_files)}] {filename}: {text}")
        else:
            print(f"[{i+1}/{len(mp3_files)}] {filename}: [NO AUDIO DETECTED]")

    # Write metadata.csv
    # We write it to the parent of the folder_path (assuming folder_path is 'processed')
    # Or just inside.
    # Piper expects metadata.csv next to wavs usually.
    
    out_path = os.path.join(folder_path, "metadata.csv")
    with open(out_path, "w", encoding="utf-8") as f:
        for line in results:
            f.write(line + "\n")
            
    print(f"Transcription complete. Saved to {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe_inner.py <folder_path>")
        sys.exit(1)
        
    folder = sys.argv[1]
    transcribe_folder(folder)
