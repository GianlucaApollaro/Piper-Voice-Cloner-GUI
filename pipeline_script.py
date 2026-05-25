
import os
import subprocess
import sys
import shutil
import uuid

try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    from faster_whisper import WhisperModel
except ImportError:
    print("Dependencies missing! Ensure Docker image is built with faster-whisper and pydub.")
    sys.exit(1)

    # Verify GPU Access
    print("--- GPU DIAGNOSTIC ---")
    try:
        subprocess.run(["nvidia-smi"], check=False)
    except FileNotFoundError:
        print("nvidia-smi not found in container.")
    print("----------------------")

def split_audio(input_file, output_folder, min_len=1000, max_len=15000, silence_thresh=-40):
    audio = AudioSegment.from_file(input_file)
    # Adjust silence thresh relative to dBFS
    silence_thresh = audio.dBFS - 16
    
    chunks = split_on_silence(audio, min_silence_len=500, silence_thresh=silence_thresh, keep_silence=200)
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    exported_count = 0
    
    for i, chunk in enumerate(chunks):
        if len(chunk) < min_len or len(chunk) > max_len:
            continue
            
        chunk = chunk.set_frame_rate(22050).set_channels(1).set_sample_width(2)
        
        out_name = f"{base_name}_seg{i:03d}.wav"
        chunk.export(os.path.join(output_folder, out_name), format="wav")
        exported_count += 1
        
    return exported_count

def process(input_dir, output_dir, lang="it"):
    print("Loading Whisper Model (Large-v3)...")
    try:
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        print("SUCCESS: Loaded Large-v3 on GPU.")
    except Exception as e_large:
        print(f"WARNING: Large-v3 on GPU failed: {e_large}")
        try:
            print("Attempting fallback to Medium on GPU...")
            model = WhisperModel("medium", device="cuda", compute_type="float16")
            print("SUCCESS: Loaded Medium on GPU.")
        except Exception as e_med:
            print(f"WARNING: Medium on GPU failed: {e_med}")
            print("CRITICAL FALLBACK: Loading Large-v3 on CPU (int8)...")
            try:
                model = WhisperModel("large-v3", device="cpu", compute_type="int8")
                print("SUCCESS: Loaded Large-v3 on CPU.")
            except Exception as e_cpu:
                 print(f"ERROR: CPU Fallback also failed: {e_cpu}")
                 sys.exit(1)

    metadata_path = os.path.join(output_dir, "metadata.csv")
    
    # RESUME LOGIC: Load existing IDs
    existing_ids = set()
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                         existing_ids.add(line.split("|")[0])
            print(f"Resuming: Found {len(existing_ids)} already processed files.", flush=True)
        except:
            print("Warning: Could not read existing metadata. Starting fresh.", flush=True)

    # Clean output dir
    wav_output_dir = os.path.join(output_dir, "wavs") 
    
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp3', '.wav', '.ogg', '.flac'))]
    print(f"Found {len(files)} audio files.", flush=True)
    
    # Generate Unique Temp Dir to avoid collisions
    run_id = uuid.uuid4().hex[:8]
    temp_chunks = os.path.join(output_dir, f"temp_chunks_{run_id}")
    print(f"Using temp directory: {temp_chunks}")

    for f in files:
        f_path = os.path.join(input_dir, f)
        print(f"Processing {f}...", flush=True)
        
        # Generate Unique Temp Dir for this file's chunks to avoid any collision risk
        # Although we have a main temp dir, let's keep it clean or just use the main one.
        # The main unique dir is already safe.
        
        if os.path.exists(temp_chunks):
            try:
                shutil.rmtree(temp_chunks)
            except:
                pass
        try:
            os.makedirs(temp_chunks)
        except:
            pass
        
        try:
            print(f"  [CPU] Splitting audio...", flush=True)
            count = split_audio(f_path, temp_chunks)
            print(f"  -> Generated {count} segments.", flush=True)
        except Exception as e:
            print(f"  -> Error splitting: {e}", flush=True)
            continue

        chunk_files = sorted([x for x in os.listdir(temp_chunks) if x.endswith('.wav')])
        
        processed_segments = 0
        
        for cf in chunk_files:
                current_file_id = os.path.splitext(cf)[0]
                final_wav_path = os.path.join(output_dir, cf)
                
                # GRANULAR RESUME CHECK
                if current_file_id in existing_ids and os.path.exists(final_wav_path):
                    # print(f"  -> Skipping {cf} (Already done)", flush=True)
                    continue

                cf_path = os.path.join(temp_chunks, cf)
                
                try:
                    # print(f"  [GPU] Transcribing {cf}...", flush=True)
                    segments, _ = model.transcribe(cf_path, language=lang, task="transcribe")
                    text = " ".join([s.text for s in segments]).strip().replace("\n", " ").replace("|", "")
                    
                    if text and len(text) > 3:
                        # Sanity Check: If text is impossibly long for a segment (max 15s), it's a hallucination.
                        # 15s of speech is roughly 30-50 words, maybe 200-300 chars max.
                        # We set a loose limit of 500 chars to be safe but catch the 44k monsters.
                        if len(text) > 500:
                            print(f"Warning: Hallucination detected for {cf}. Text length {len(text)} > 500. Skipping.")
                            continue

                        try:
                            shutil.move(cf_path, final_wav_path)
                            
                            # Write immediately - Open/Close each time to minimize lock for Studio
                            try:
                                with open(metadata_path, "a", encoding="utf-8") as meta_f:
                                    line = f"{current_file_id}|{text}"
                                    meta_f.write(line + "\n")
                            except Exception as e_write:
                                print(f"Error writing metadata for {cf}: {e_write}")
                            
                            # Add to existing_ids to prevent processing if code loops or whatever
                            existing_ids.add(current_file_id)
                            processed_segments += 1
                        except FileNotFoundError:
                            print(f"Warning: File {cf} missing during move. Skipping.")
                        except Exception as e:
                            print(f"Error moving {cf}: {e}")
                except Exception as e:
                    print(f"Error transcribing {cf}: {e}")
        
        if processed_segments > 0:
            print(f"  -> Transcribed and saved {processed_segments} new segments.", flush=True)
            
        if os.path.exists(temp_chunks):
            shutil.rmtree(temp_chunks)
            
    print("DONE_PIPELINE", flush=True)
        


if __name__ == "__main__":
    target_lang = "it"
    if len(sys.argv) > 1:
        target_lang = sys.argv[1]
    process("/input", "/output", lang=target_lang)
