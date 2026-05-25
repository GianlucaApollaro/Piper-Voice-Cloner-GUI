"""
Analyze wav files to detect audio energy at the first and last samples.
Write results to a text file.
"""
import os
import struct
import wave

def analyze_wav_edges(wav_path, edge_ms=15):
    try:
        with wave.open(wav_path, 'rb') as w:
            rate = w.getframerate()
            n_frames = w.getnframes()
            sw = w.getsampwidth()
            edge_frames = int(rate * edge_ms / 1000)
            
            w.rewind()
            head_data = w.readframes(min(edge_frames, n_frames))
            
            start_pos = max(0, n_frames - edge_frames)
            w.setpos(start_pos)
            tail_data = w.readframes(edge_frames)
            
            def rms(data, sample_width):
                if sample_width == 2:
                    fmt = "<" + str(len(data)//2) + "h"
                    samples = struct.unpack(fmt, data)
                else:
                    return 0
                if not samples:
                    return 0
                return (sum(s*s for s in samples) / len(samples)) ** 0.5
            
            head_rms = rms(head_data, sw)
            tail_rms = rms(tail_data, sw)
            duration_ms = n_frames / rate * 1000
            return head_rms, tail_rms, duration_ms
    except Exception as e:
        return 0, 0, 0

def main():
    processed_dir = r"F:\evan\more\processed"
    out_file = r"c:\piper_ui\changes\cut_analysis.txt"
    
    meta_path = os.path.join(processed_dir, "metadata.csv")
    meta = {}
    with open(meta_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|', 1)
            if len(parts) == 2:
                meta[parts[0]] = parts[1]
    
    wavs = sorted([f for f in os.listdir(processed_dir) if f.endswith('.wav')])
    
    THRESHOLD = 500
    
    lines = []
    bad_cuts = []
    
    for wav in wavs:
        path = os.path.join(processed_dir, wav)
        h_rms, t_rms, dur = analyze_wav_edges(path, edge_ms=15)
        
        basename = os.path.splitext(wav)[0]
        text = meta.get(basename, "???")
        text_end = text[-40:] if len(text) > 40 else text
        
        head_hot = "YES" if h_rms > THRESHOLD else ""
        tail_hot = "YES" if t_rms > THRESHOLD else ""
        
        if head_hot or tail_hot:
            bad_cuts.append((wav, head_hot, tail_hot, h_rms, t_rms, text_end))
        
        lines.append("{:<20} | {:<10.0f} | {:<10.0f} | {:<10.0f} | {:<6} | {:<6} | ...{}".format(
            wav, h_rms, t_rms, dur, head_hot, tail_hot, text_end))
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("=== ALL FILES ===\n")
        f.write("{:<20} | {:<10} | {:<10} | {:<10} | {:<6} | {:<6} | Text\n".format(
            "File", "Head RMS", "Tail RMS", "Dur(ms)", "Head?", "Tail?"))
        f.write("-" * 120 + "\n")
        for line in lines:
            f.write(line + "\n")
        
        f.write("\n\n=== POTENTIAL BAD CUTS ({} files) ===\n".format(len(bad_cuts)))
        for wav, h, t, hr, tr, txt in bad_cuts:
            flags = []
            if h: flags.append("AUDIO AT START (rms={:.0f})".format(hr))
            if t: flags.append("AUDIO AT END (rms={:.0f})".format(tr))
            f.write("  {}: {} | ...{}\n".format(wav, ', '.join(flags), txt))

if __name__ == "__main__":
    main()
