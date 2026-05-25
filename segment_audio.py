import os
import sys
import shutil
import re
import tempfile
import time
from contextlib import contextmanager

try:
    from faster_whisper import WhisperModel
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
except ImportError:
    print("Dependencies missing! Ensure Docker image is built with faster-whisper and pydub.")
    sys.exit(1)

# --- CONFIGURATION ---
# Silence Splitting (Defaults)
MIN_SILENCE_LEN = 500   # ms
SILENCE_THRESH_DEFAULT = -32  # dB absolute
KEEP_SILENCE = 300      # ms

# Duration Constraints
TARGET_DURATION = 10.0  # seconds
MIN_DURATION = 0.5      # seconds; too-short clips often produce Whisper restarts
MAX_DURATION = 15.0     # seconds; Piper-friendly hard limit
FALLBACK_SPLIT_MS = 12000  # used only when silence split leaves a chunk too large
MAX_TEXT_CHARS = 220
MAX_WORDS = 45
MAX_CHARS_PER_WORD = 40
MAX_PUNCT_RUN = 8
MAX_CHARS_PER_SECOND = 28
MAX_WORDS_PER_SECOND = 5.2
MAX_SINGLE_SEGMENT_CHARS = 500
LOCK_TIMEOUT_SECONDS = 30
LOCK_POLL_INTERVAL_SECONDS = 0.2


print("=" * 60, flush=True)
print("  SEGMENT_AUDIO v4.6 - CSV-SAFE METADATA + NO HARD TIME CUTS", flush=True)
print("  Waiting for runtime duration settings...", flush=True)
print("=" * 60, flush=True)


def sanitize_duration_settings(target_duration: float, max_duration: float, min_duration: float) -> tuple[float, float, float]:
    """Defend against bad UI/CLI wiring so sane chunks do not get discarded."""
    try:
        target_duration = float(target_duration)
    except Exception:
        target_duration = 10.0
    try:
        max_duration = float(max_duration)
    except Exception:
        max_duration = 15.0
    try:
        min_duration = float(min_duration)
    except Exception:
        min_duration = 0.5

    if target_duration <= 0:
        print(f"Warning: invalid target_duration={target_duration}; resetting to 10.0", flush=True)
        target_duration = 10.0

    if max_duration <= 0:
        print(f"Warning: invalid max_duration={max_duration}; resetting to 15.0", flush=True)
        max_duration = 15.0

    if max_duration < target_duration:
        print(f"Warning: max_duration {max_duration} is below target_duration {target_duration}; raising max_duration to {target_duration}", flush=True)
        max_duration = target_duration

    if min_duration < 0:
        print(f"Warning: invalid min_duration={min_duration}; resetting to 0.5", flush=True)
        min_duration = 0.5

    # A "tiny chunk" floor should stay tiny. If UI wiring accidentally feeds
    # target/max values into min_duration, repair it instead of skipping everything.
    if min_duration >= max_duration or min_duration >= target_duration or min_duration > 3.0:
        print(
            f"Warning: min_duration={min_duration} looks unsafe for chunk filtering; resetting to 0.5 seconds.",
            flush=True,
        )
        min_duration = 0.5

    return target_duration, max_duration, min_duration


def contains_numbers(text: str) -> bool:
    """Return True if transcript contains any digit characters."""
    return any(char.isdigit() for char in text)



def normalize_text(text: str) -> str:
    """Basic cleanup without rewriting the actual transcript content."""
    text = text.replace("\r", " ").replace("\n", " ").replace("|", " ")
    # Prevent csv.reader in later Piper stages from treating metadata lines as quoted multiline fields.
    text = text.replace('"', "'")
    text = re.sub(r"\s+", " ", text).strip()

    while text and text[0] in [',', '.', ';', ':', '-', '—', '!', '?', ')', ']']:
        text = text[1:].strip()

    if not text:
        return ""

    if text[-1] not in ['.', '!', '?']:
        if text[-1] in [',', ';', ':', '-']:
            text = text[:-1] + "."
        else:
            text += "."

    return text


def remove_immediate_duplicate_phrases(text: str) -> str:
    """
    Remove obvious Whisper restart artifacts like:
    '... he was rubbing his eyes ... he was rubbing his eyes ...'
    while avoiding heavy-handed rewriting.
    """
    words = text.split()
    if len(words) < 8:
        return text

    changed = True
    while changed:
        changed = False
        n = len(words)
        # Look for immediately repeated windows of 4-12 words
        for size in range(12, 3, -1):
            i = 0
            while i + 2 * size <= n:
                left = [w.lower() for w in words[i:i + size]]
                right = [w.lower() for w in words[i + size:i + 2 * size]]
                if left == right:
                    del words[i + size:i + 2 * size]
                    n = len(words)
                    changed = True
                else:
                    i += 1
            if changed:
                break

    return " ".join(words)


def has_bad_restart_pattern(text: str) -> bool:
    """Catch the ugliest repeated-clause rows before they hit metadata.csv."""
    lower = re.sub(r"[^a-z0-9\s']", " ", text.lower())
    lower = re.sub(r"\s+", " ", lower).strip()
    words = lower.split()
    if len(words) < 10:
        return False

    # Flag if the same 5-8 word phrase appears more than once.
    for size in range(8, 4, -1):
        seen = {}
        for i in range(0, len(words) - size + 1):
            phrase = tuple(words[i:i + size])
            seen[phrase] = seen.get(phrase, 0) + 1
            if seen[phrase] >= 2:
                return True
    return False


def looks_like_embedded_metadata(text: str) -> bool:
    """Detect cases where another metadata row got swallowed into the transcript."""
    if "|" in text:
        return True

    # Segment-id-like patterns appearing mid-text are a bad sign.
    if re.search(r"\b[^\s|]{1,80}_\d{4}\b", text):
        return True

    # Common swallowed metadata forms such as:
    # "02 - Track02_0008|" or "some name_0012"
    if re.search(r"\b(?:track\d+|chapter\d+|part\d+|disc\d+)?[^\n\r|]{0,80}_\d{4}(?:\.wav)?\b", text, re.IGNORECASE):
        return True

    # A transcript should never contain what looks like another metadata row start.
    if re.search(r"(?:^|\s)[^\s|]{1,120}\|[^|]{1,200}$", text):
        return True

    return False


def has_pathological_text_shape(text: str) -> tuple[bool, str]:
    """Catch text that is formally valid but dangerous for Piper attention."""
    words = text.split()

    if len(text) > MAX_TEXT_CHARS:
        return True, f"text length {len(text)} exceeds {MAX_TEXT_CHARS} chars"

    if len(words) > MAX_WORDS:
        return True, f"word count {len(words)} exceeds {MAX_WORDS}"

    longest_word = max((len(w) for w in words), default=0)
    if longest_word > MAX_CHARS_PER_WORD:
        return True, f"contains overlong token ({longest_word} chars)"

    if re.search(r"([,.;:!?\-—])\1{%d,}" % (MAX_PUNCT_RUN - 1), text):
        return True, "contains pathological punctuation run"

    # Repeated tiny fragments can indicate Whisper getting lost even if clause-repeat logic misses it
    if len(words) >= 12:
        repeats = 0
        for size in range(2, 5):
            seen = {}
            for i in range(0, len(words) - size + 1):
                phrase = tuple(w.lower() for w in words[i:i + size])
                seen[phrase] = seen.get(phrase, 0) + 1
                if seen[phrase] >= 4:
                    repeats += 1
                    break
        if repeats >= 2:
            return True, "contains excessive repeated short phrases"

    if looks_like_embedded_metadata(text):
        return True, "looks like embedded metadata/segment id"

    return False, ""


def has_duration_text_mismatch(text: str, duration_seconds: float | None) -> tuple[bool, str]:
    """Reject transcripts whose density is wildly implausible for the clip length."""
    if duration_seconds is None or duration_seconds <= 0:
        return False, ""

    words = text.split()
    char_count = len(text)
    word_count = len(words)

    if char_count > MAX_SINGLE_SEGMENT_CHARS:
        return True, f"text length {char_count} exceeds hard segment cap {MAX_SINGLE_SEGMENT_CHARS} chars"

    chars_per_second = char_count / duration_seconds
    words_per_second = word_count / duration_seconds if duration_seconds > 0 else float('inf')

    if chars_per_second > MAX_CHARS_PER_SECOND:
        return True, f"text density too high for clip ({chars_per_second:.1f} chars/sec)"

    if words_per_second > MAX_WORDS_PER_SECOND:
        return True, f"word density too high for clip ({words_per_second:.1f} words/sec)"

    return False, ""


def validate_metadata_line(seg_name: str, text: str, duration_seconds: float | None = None) -> tuple[bool, str]:
    if not seg_name.strip():
        return False, "blank segment id"

    if not text.strip():
        return False, "blank transcript"

    if "\n" in text or "\r" in text:
        return False, "newline in transcript"

    if '"' in text:
        return False, 'raw double quote in transcript'

    bad_shape, reason = has_pathological_text_shape(text)
    if bad_shape:
        return False, reason

    duration_mismatch, reason = has_duration_text_mismatch(text, duration_seconds)
    if duration_mismatch:
        return False, reason

    return True, ""


def fallback_split_chunk(chunk: AudioSegment, max_ms: int = int(MAX_DURATION * 1000)):
    """
    Split an oversized chunk only at detected silence boundaries.

    Older builds used fixed time slices here, for example chunk[0:15000],
    chunk[15000:30000], etc. That kept the tail audio, but it could cut
    directly through a word, breath, consonant, or vowel. That is unsafe for
    Piper training because the model may learn clipped speech as valid speech.

    This function now tries progressively more permissive silence detection.
    If a section still cannot be brought under max_ms without a silence
    boundary, it is rejected instead of being hard-cut. Losing an unsafe row is
    better than teaching clipped audio.
    """
    if max_ms <= 0:
        print("  Refusing oversized split: max duration is invalid.", flush=True)
        return []

    if len(chunk) <= max_ms:
        return [chunk]

    total_sec = len(chunk) / 1000.0
    max_sec = max_ms / 1000.0

    # Use both absolute and relative thresholds. The relative thresholds adapt
    # to very quiet or very loud source files; the absolute thresholds provide
    # sane fallback behavior for ordinary speech recordings.
    dbfs = chunk.dBFS
    threshold_candidates = [-45, -40, -36, -32, -28]
    if dbfs != float("-inf"):
        threshold_candidates.extend([dbfs - 24, dbfs - 20, dbfs - 16, dbfs - 12])

    # Remove duplicates while preserving order. Round to avoid tiny float noise.
    seen_thresholds = set()
    thresholds = []
    for thresh in threshold_candidates:
        rounded = round(float(thresh), 1)
        if rounded not in seen_thresholds:
            seen_thresholds.add(rounded)
            thresholds.append(rounded)

    # Start conservative. Only become more aggressive if the chunk would
    # otherwise be rejected. These are still silence-based cuts, not time cuts.
    min_silence_candidates = [500, 350, 250, 180, 120]

    best_partial = []
    best_partial_ms = 0
    best_partial_note = ""

    for min_silence in min_silence_candidates:
        for thresh in thresholds:
            try:
                pieces = split_on_silence(
                    chunk,
                    min_silence_len=min_silence,
                    silence_thresh=thresh,
                    keep_silence=KEEP_SILENCE,
                )
            except Exception as e:
                print(f"  Silence fallback attempt failed: {e}", flush=True)
                continue

            if len(pieces) <= 1:
                continue

            accepted = []
            rejected_oversized = 0
            rejected_tiny = 0

            for piece in pieces:
                piece_sec = len(piece) / 1000.0
                if len(piece) > max_ms:
                    rejected_oversized += 1
                    continue
                if piece_sec < MIN_DURATION:
                    rejected_tiny += 1
                    continue
                accepted.append(piece)

            accepted_ms = sum(len(piece) for piece in accepted)
            if accepted and accepted_ms > best_partial_ms:
                best_partial = accepted
                best_partial_ms = accepted_ms
                best_partial_note = (
                    f"min_silence={min_silence}ms, threshold={thresh:.1f} dBFS, "
                    f"rejected_oversized={rejected_oversized}, rejected_tiny={rejected_tiny}"
                )

            if accepted and rejected_oversized == 0:
                print(
                    f"  Safely split oversized chunk ({total_sec:.2f}s) into "
                    f"{len(accepted)} silence-bounded piece(s) using "
                    f"min_silence={min_silence}ms, threshold={thresh:.1f} dBFS."
                    + (f" Rejected {rejected_tiny} tiny piece(s)." if rejected_tiny else ""),
                    flush=True,
                )
                return accepted

    if best_partial:
        print(
            f"  Partially salvaged oversized chunk ({total_sec:.2f}s): kept "
            f"{len(best_partial)} silence-bounded piece(s), rejected the remaining "
            f"unsafely long section(s); {best_partial_note}.",
            flush=True,
        )
        return best_partial

    print(
        f"  Skipping oversized chunk ({total_sec:.2f}s > {max_sec:.2f}s): "
        "no safe silence boundary found; refusing hard time cut.",
        flush=True,
    )
    return []


def postprocess_chunks(raw_chunks, combine_clips=True, target_duration=None, max_duration=None, min_duration=None):
    """Apply merge logic plus hard duration sanity checks."""
    if target_duration is None:
        target_duration = TARGET_DURATION
    if max_duration is None:
        max_duration = MAX_DURATION
    if min_duration is None:
        min_duration = MIN_DURATION
    if not raw_chunks:
        return []

    if combine_clips:
        merged_chunks = []
        current_buffer = AudioSegment.empty()

        for chunk in raw_chunks:
            current_len_sec = len(current_buffer) / 1000.0
            chunk_len_sec = len(chunk) / 1000.0

            if chunk_len_sec > max_duration:
                if len(current_buffer) > 0:
                    merged_chunks.append(current_buffer)
                    current_buffer = AudioSegment.empty()
                merged_chunks.extend(fallback_split_chunk(chunk, int(max_duration * 1000)))
                continue

            if (current_len_sec + chunk_len_sec) > max_duration:
                if len(current_buffer) > 0:
                    merged_chunks.append(current_buffer)
                current_buffer = chunk
            elif (current_len_sec + chunk_len_sec) >= target_duration:
                current_buffer += chunk
                merged_chunks.append(current_buffer)
                current_buffer = AudioSegment.empty()
            else:
                current_buffer += chunk

        if len(current_buffer) > 0:
            merged_chunks.append(current_buffer)
    else:
        merged_chunks = []
        for chunk in raw_chunks:
            if len(chunk) > max_duration * 1000:
                merged_chunks.extend(fallback_split_chunk(chunk, int(max_duration * 1000)))
            else:
                merged_chunks.append(chunk)

    # Final pass: skip tiny junk clips that are likely to cause Whisper restarts
    final_chunks = []
    for chunk in merged_chunks:
        dur_sec = len(chunk) / 1000.0
        if dur_sec < min_duration:
            print(f"  Skipping tiny chunk ({dur_sec:.2f}s) to avoid bad transcriptions.", flush=True)
            continue
        final_chunks.append(chunk)

    return final_chunks


@contextmanager
def metadata_lock(lock_path: str, timeout: float = LOCK_TIMEOUT_SECONDS):
    """Simple cross-process lock using exclusive file creation."""
    start = time.time()
    fd = None
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8", errors="ignore"))
            break
        except FileExistsError:
            if (time.time() - start) >= timeout:
                raise TimeoutError(f"Timed out waiting for metadata lock: {lock_path}")
            time.sleep(LOCK_POLL_INTERVAL_SECONDS)

    try:
        yield
    finally:
        try:
            if fd is not None:
                os.close(fd)
        finally:
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except FileNotFoundError:
                pass


def load_valid_metadata_rows(metadata_path: str):
    """Read and validate existing metadata, returning only safe rows."""
    valid_rows = []
    existing_ids = set()

    if not os.path.exists(metadata_path):
        return valid_rows, existing_ids

    with open(metadata_path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if '|' not in line:
                print(f"Skipping malformed existing metadata row (no pipe): {line[:80]}", flush=True)
                continue

            seg_id, seg_text = line.split('|', 1)
            seg_id = seg_id.strip()
            seg_text = seg_text.strip()

            is_valid, reason = validate_metadata_line(seg_id, seg_text)
            if not is_valid:
                print(f"Skipping malformed existing metadata row for {seg_id or '[blank]'}: {reason}.", flush=True)
                continue

            if seg_id in existing_ids:
                print(f"Skipping duplicate existing metadata row for {seg_id}.", flush=True)
                continue

            valid_rows.append((seg_id, seg_text))
            existing_ids.add(seg_id)

    return valid_rows, existing_ids


def atomic_rewrite_metadata(metadata_path: str, rows):
    """Rewrite metadata.csv atomically using only validated rows."""
    metadata_dir = os.path.dirname(metadata_path) or '.'
    fd, temp_path = tempfile.mkstemp(prefix='metadata_', suffix='.tmp', dir=metadata_dir, text=True)

    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as temp_f:
            for seg_id, seg_text in rows:
                temp_f.write(f"{seg_id}|{seg_text}\n")
            temp_f.flush()
            os.fsync(temp_f.fileno())

        os.replace(temp_path, metadata_path)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise


def safe_update_metadata(metadata_path: str, new_lines):
    """Validate, merge, and atomically rewrite metadata under a lock."""
    lock_path = metadata_path + '.lock'

    with metadata_lock(lock_path):
        valid_rows, existing_ids = load_valid_metadata_rows(metadata_path)

        added = 0
        for line in new_lines:
            if '|' not in line:
                print(f"  Refusing malformed metadata line (no pipe): {line[:80]}", flush=True)
                continue

            seg_id, seg_text = line.split('|', 1)
            seg_id = seg_id.strip()
            seg_text = seg_text.strip()

            is_valid, reason = validate_metadata_line(seg_id, seg_text)
            if not is_valid:
                print(f"  Refusing metadata write for {seg_id or '[blank]'}: {reason}.", flush=True)
                continue

            if seg_id in existing_ids:
                continue

            valid_rows.append((seg_id, seg_text))
            existing_ids.add(seg_id)
            added += 1

        atomic_rewrite_metadata(metadata_path, valid_rows)
        return added


def process_file(input_file, output_dir, model, lang="it", silence_thresh=None, min_silence_len=None, is_relative=False, combine_clips=True, target_duration=None, max_duration=None, min_duration=None, reject_numbers=False):
    if target_duration is None:
        target_duration = TARGET_DURATION
    if max_duration is None:
        max_duration = MAX_DURATION
    if min_duration is None:
        min_duration = MIN_DURATION
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    print(f"Loading {base_name}...", flush=True)
    try:
        audio = AudioSegment.from_file(input_file)
    except Exception as e:
        print(f"Error loading audio: {e}", flush=True)
        return []

    print("Splitting on silence (Safe Mode)...", flush=True)

    actual_min_len = min_silence_len if min_silence_len is not None else MIN_SILENCE_LEN
    actual_thresh_val = silence_thresh if silence_thresh is not None else SILENCE_THRESH_DEFAULT

    if is_relative:
        thresh = audio.dBFS + actual_thresh_val
        print(f"  -> Using RELATIVE threshold: {thresh:.1f} dBFS (audio.dBFS {audio.dBFS:.1f} + offset {actual_thresh_val})", flush=True)
    else:
        thresh = actual_thresh_val
        print(f"  -> Using ABSOLUTE threshold: {thresh} dB", flush=True)

    print(f"  -> Min silence length: {actual_min_len} ms", flush=True)

    raw_chunks = split_on_silence(
        audio,
        min_silence_len=actual_min_len,
        silence_thresh=thresh,
        keep_silence=KEEP_SILENCE,
    )

    print(f"  -> Generated {len(raw_chunks)} raw fragments.", flush=True)

    if not raw_chunks:
        print("Warning: No silence found. Using entire file, then trying safe no-hard-cut fallback split.", flush=True)
        raw_chunks = [audio]

    final_chunks = postprocess_chunks(raw_chunks, combine_clips=combine_clips, target_duration=target_duration, max_duration=max_duration, min_duration=min_duration)
    print(f"  -> Prepared {len(final_chunks)} final segments.", flush=True)

    metadata_lines = []
    temp_work_dir = os.path.join(output_dir, "temp_transcribe")
    os.makedirs(temp_work_dir, exist_ok=True)
    wavs_dir = os.path.join(output_dir, "wavs")
    os.makedirs(wavs_dir, exist_ok=True)

    for i, segment in enumerate(final_chunks):
        seg_name = f"{base_name}_{i:04d}"
        temp_path = os.path.join(temp_work_dir, f"{seg_name}.wav")
        final_path = os.path.join(wavs_dir, f"{seg_name}.wav")

        try:
            segment = segment.set_frame_rate(22050).set_channels(1).set_sample_width(2)
            segment.export(temp_path, format="wav")
        except Exception as e:
            print(f"  Error exporting {seg_name}: {e}", flush=True)
            continue

        try:
            segments, _ = model.transcribe(temp_path, language=lang, task="transcribe")
            text = " ".join([s.text for s in segments]).strip()
            text = normalize_text(text)
            text = remove_immediate_duplicate_phrases(text)
            text = normalize_text(text)
            segment_duration_seconds = len(segment) / 1000.0

            if not text:
                print(f"  Skipping empty segment {seg_name}", flush=True)
                continue

            if reject_numbers and contains_numbers(text):
                print(f"  Skipping {seg_name}: contains numbers.", flush=True)
                continue

            if has_bad_restart_pattern(text):
                print(f"  Skipping {seg_name}: repeated-clause restart pattern detected.", flush=True)
                continue

            is_valid, reason = validate_metadata_line(seg_name, text, segment_duration_seconds)
            if not is_valid:
                print(f"  Skipping {seg_name}: {reason}.", flush=True)
                continue

            shutil.move(temp_path, final_path)
            metadata_lines.append(f"{seg_name}|{text}")
        except Exception as e:
            print(f"  Error transcribing {seg_name}: {e}", flush=True)
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    try:
        shutil.rmtree(temp_work_dir)
    except Exception:
        pass

    return metadata_lines


# --- MAIN ---

def main(input_dir, output_dir, lang="it", silence_thresh=None, min_silence_len=None, is_relative=False, combine_clips=True, target_duration=10.0, max_duration=15.0, min_duration=0.5, reject_numbers=False):
    global TARGET_DURATION, MAX_DURATION, MIN_DURATION
    target_duration, max_duration, min_duration = sanitize_duration_settings(target_duration, max_duration, min_duration)
    TARGET_DURATION = target_duration
    MAX_DURATION = max_duration
    MIN_DURATION = min_duration
    print(f"Runtime duration settings -> Merge Target: {TARGET_DURATION}s | Hard Max: {MAX_DURATION}s | Min Chunk: {MIN_DURATION}s", flush=True)
    print(f"Sanitized duration settings -> target_duration={TARGET_DURATION}, max_duration={MAX_DURATION}, min_duration={MIN_DURATION}", flush=True)
    print("Loading Whisper Model...", flush=True)
    try:
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:
        print("Fallback to medium/CPU...", flush=True)
        model = WhisperModel("medium", device="cpu", compute_type="int8")

    os.makedirs(output_dir, exist_ok=True)
    wavs_dir = os.path.join(output_dir, "wavs")
    os.makedirs(wavs_dir, exist_ok=True)
    metadata_path = os.path.join(output_dir, "metadata.csv")

    # Initial validation/repair pass so old malformed rows do not linger forever.
    initial_rows, initial_ids = load_valid_metadata_rows(metadata_path)
    if os.path.exists(metadata_path):
        try:
            atomic_rewrite_metadata(metadata_path, initial_rows)
            print(f"Validated existing metadata: kept {len(initial_rows)} safe rows.", flush=True)
        except Exception as e:
            print(f"Warning: could not rewrite existing metadata safely: {e}", flush=True)

    files = sorted(
        [f for f in os.listdir(input_dir) if f.lower().endswith((('.mp3', '.wav', '.ogg', '.flac')))]
    )

    for f in files:
        f_path = os.path.join(input_dir, f)
        try:
            meta_lines = process_file(
                input_file=f_path,
                output_dir=output_dir,
                model=model,
                lang=lang,
                silence_thresh=silence_thresh,
                min_silence_len=min_silence_len,
                is_relative=is_relative,
                combine_clips=combine_clips,
                target_duration=target_duration,
                max_duration=max_duration,
                min_duration=min_duration,
                reject_numbers=reject_numbers,
            )

            if meta_lines:
                try:
                    added = safe_update_metadata(metadata_path, meta_lines)
                    if added:
                        print(f"  Safely wrote {added} metadata rows.", flush=True)
                except Exception as e:
                    print(f"  Error updating metadata safely: {e}", flush=True)
        except Exception as e:
            print(f"Error processing {f}: {e}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python segment_audio.py <input_dir> <output_dir> [lang] [silence_thresh] [min_silence_len] [is_relative_int] [combine_clips_int] [target_duration] [max_duration] [min_duration] [reject_numbers_int]")
        sys.exit(1)

    in_d = sys.argv[1]
    out_d = sys.argv[2]
    lng = sys.argv[3] if len(sys.argv) > 3 else "it"

    thresh = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != "" else None
    min_len = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] != "" else None
    is_rel = bool(int(sys.argv[6])) if len(sys.argv) > 6 and sys.argv[6] != "" else False
    combine = bool(int(sys.argv[7])) if len(sys.argv) > 7 and sys.argv[7] != "" else True
    
    target_dur = float(sys.argv[8]) if len(sys.argv) > 8 and sys.argv[8] != "" else 10.0
    max_dur = float(sys.argv[9]) if len(sys.argv) > 9 and sys.argv[9] != "" else 15.0
    min_dur = float(sys.argv[10]) if len(sys.argv) > 10 and sys.argv[10] != "" else 0.5
    reject_numbers = bool(int(sys.argv[11])) if len(sys.argv) > 11 and sys.argv[11] != "" else False

    print(f"CLI settings -> lang={lng}, silence_thresh={thresh}, min_silence_len={min_len}, is_relative={is_rel}, combine_clips={combine}, target_duration={target_dur}, max_duration={max_dur}, min_duration={min_dur}, reject_numbers={reject_numbers}", flush=True)
    main(in_d, out_d, lng, thresh, min_len, is_rel, combine, target_dur, max_dur, min_dur, reject_numbers)
