
def simulate_splits(gaps):
    # v2.3 Configuration
    HEAD_PADDING = 0.12
    TAIL_PADDING = 0.30
    WHISPER_END_OFFSET = 0.25
    
    print(f"{'Gap (ms)':<10} | {'Prev Tail':<10} | {'Next Head':<10} | {'Split Delta':<12} | {'Notes'}")
    print("-" * 75)
    
    for gap_s in gaps:
        # Word A ends at 1.0s
        # Word B starts at 1.0 + gap_s
        
        # New Logic Simulation (simplified from segment_audio.py)
        # TAIL END (t_end)
        adj_end = 1.0 + WHISPER_END_OFFSET
        raw_mid = (1.0 + (1.0 + gap_s)) / 2.0
        
        if adj_end < (1.0 + gap_s):
            t_end = max(raw_mid, adj_end)
            t_end = min(t_end, (1.0 + gap_s) - 0.005)
        else:
            t_end = raw_mid
            
        tail_room = t_end - 1.0
        
        # HEAD START (t_start)
        # Mirror: previous word (A) ends at 1.0
        # our word (B) starts at 1.0 + gap_s
        raw_mid_start = (1.0 + (1.0 + gap_s)) / 2.0
        if adj_end < (1.0 + gap_s):
            t_start = max(raw_mid_start, adj_end)
            t_start = min(t_start, (1.0 + gap_s) - 0.005)
        else:
            t_start = raw_mid_start
            
        head_room = (1.0 + gap_s) - t_start
        
        # Delta = Gap between file segments (should be tiny or 0 if overlapping/continuous)
        delta = t_start - t_end
        
        note = ""
        if tail_room >= gap_s:
            note = "CLIPS NEXT!"
        elif tail_room < 0.15:
            note = "RISKY (Under 150ms)"
        elif gap_s < 0.15:
            note = "Tight Gap (Handled)"
        else:
            note = "Safe"
            
        print(f"{gap_s*1000:<10.0f} | {tail_room*1000:<10.1f} | {head_room*1000:<10.1f} | {delta*1000:<12.1f} | {note}")

gaps = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.80]
simulate_splits(gaps)
