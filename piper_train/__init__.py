from hashlib import sha256
from pathlib import Path
from typing import Optional, Tuple, Union

import librosa
import torch

from piper_train.vits.mel_processing import spectrogram_torch

from .trim import trim_silence
from .vad import SileroVoiceActivityDetector

_DIR = Path(__file__).parent


def make_silence_detector() -> SileroVoiceActivityDetector:
    silence_model = _DIR / "models" / "silero_vad.onnx"
    return SileroVoiceActivityDetector(silence_model)


def cache_norm_audio(
    audio_path: Union[str, Path],
    cache_dir: Union[str, Path],
    detector: SileroVoiceActivityDetector,
    sample_rate: int,
    silence_threshold: float = 0.2,
    silence_samples_per_chunk: int = 480,
    silence_keep_chunks_before: int = 2,
    silence_keep_chunks_after: int = 2,
    filter_length: int = 1024,
    window_length: int = 1024,
    hop_length: int = 256,
    ignore_cache: bool = False,
) -> Tuple[Path, Path]:
    audio_path = Path(audio_path).absolute()
    cache_dir = Path(cache_dir)

    # Cache id includes source path and processing parameters so stale cache
    # entries are not silently reused after settings change.
    cache_key = "|".join(
        [
            str(audio_path),
            str(sample_rate),
            str(silence_threshold),
            str(silence_samples_per_chunk),
            str(silence_keep_chunks_before),
            str(silence_keep_chunks_after),
            str(filter_length),
            str(window_length),
            str(hop_length),
        ]
    )
    audio_cache_id = sha256(cache_key.encode()).hexdigest()

    audio_norm_path = cache_dir / f"{audio_cache_id}.pt"
    audio_spec_path = cache_dir / f"{audio_cache_id}.spec.pt"

    # Normalize audio
    audio_norm_tensor: Optional[torch.FloatTensor] = None
    if ignore_cache or (not audio_norm_path.exists()):
        # Trim silence first.
        #
        # The VAD model works on 16khz, so we determine the portion of audio
        # to keep and then just load that with librosa.
        vad_sample_rate = 16000
        detector.reset()
        audio_16khz, _sr = librosa.load(path=audio_path, sr=vad_sample_rate)

        offset_sec, duration_sec = trim_silence(
            audio_16khz,
            detector,
            threshold=silence_threshold,
            samples_per_chunk=silence_samples_per_chunk,
            sample_rate=vad_sample_rate,
            keep_chunks_before=silence_keep_chunks_before,
            keep_chunks_after=silence_keep_chunks_after,
        )

        # NOTE: audio is already in [-1, 1] coming from librosa
        audio_norm_array, _sr = librosa.load(
            path=audio_path,
            sr=sample_rate,
            offset=offset_sec,
            duration=duration_sec,
        )

        if audio_norm_array.size == 0:
            raise ValueError(f"Trimmed audio is empty: {audio_path}")

        # Save to cache directory
        audio_norm_tensor = torch.FloatTensor(audio_norm_array).unsqueeze(0)
        torch.save(audio_norm_tensor, audio_norm_path)

    # Compute spectrogram
    if ignore_cache or (not audio_spec_path.exists()):
        if audio_norm_tensor is None:
            # Load pre-cached normalized audio
            audio_norm_tensor = torch.load(audio_norm_path)

        audio_spec_tensor = spectrogram_torch(
            y=audio_norm_tensor,
            n_fft=filter_length,
            sampling_rate=sample_rate,
            hop_size=hop_length,
            win_size=window_length,
            center=False,
        ).squeeze(0)
        torch.save(audio_spec_tensor, audio_spec_path)

    return audio_norm_path, audio_spec_path
