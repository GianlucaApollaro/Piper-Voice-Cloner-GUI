def check_tail_logic(gap):
    # v2.4 Logic
    safe_tail = 1.0 + 0.12
    safe_head = (1.0 + gap) - 0.02
    
    if safe_tail < safe_head:
        t_end = (safe_tail + safe_head) / 2.0
    else:
        t_end = (1.0 + (1.0 + gap)) / 2.0
    
    t_end = min(t_end, (1.0 + gap) - 0.01)
    return t_end - 1.0

# Test cases
gaps = [0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.6]
with open("test_results.txt", "w") as f:
    f.write(f"{'Gap':<10} | {'Tail Room':<10} | {'Next Start Offset':<10}\n")
    f.write("-" * 35 + "\n")
for g in gaps:
    tr = check_tail_logic(g)
    # Next word starts at 'end + gap'. 
    # Cut point is 'end + tr'.
    # Overlap into next word = tr - gap (if positive)
    overlap = tr - g
    with open("test_results.txt", "a") as f:
        f.write(f"{g:<10.3f} | {tr:<10.3f} | {overlap:<10.3f}\n")
