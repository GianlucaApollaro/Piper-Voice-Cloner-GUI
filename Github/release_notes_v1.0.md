# Piper Voice Cloner GUI v1.0 - Initial Release

An advanced, Docker-powered Graphical User Interface (wxPython) for voice cloning, training, testing, and exporting **Piper VITS** voice models. Fully optimized for high-performance NVIDIA Graphics Cards (including RTX 50-series/RTX 5070) with native PyTorch Nightly cu128 / CUDA 12.8 support.

## Key Features

### 🚀 Performance & Infrastructure
- **RTX 50-Series Optimization**: Dynamic batch sizing and support for 16-bit Mixed Precision training.
- **Persistent Local Caching**: Automatic caching of Faster-Whisper models (V3) to reduce startup latency and save network bandwidth.

### 🎙️ Dataset Ingestion & Whisper Pipelines
- **Prosody-First Audio Slicing**: Splits long audio recordings into natural narration chunks (2-15 seconds) based on silence structure.
- **Automated Whisper Transcripts**: Fast parallel transcription via Whisper.
- **Zero-Shot Automatic Audio Translation**: Translate audio files directly from any language to target dialects (Italian, Spanish, French, German, or English).

### ✏️ Correction Studio
- **Full Navigation Shortcuts**: F3 (Search), F4 (Prev), F5 (Play/Listen), F6 (Next), and Ctrl+S (Save).

### 📱 iOS / Mobile ONNX compatibility
- **ONNX Metadata Enrichment**: Automatic post-processing of exported ONNX configs to enrich language tags (`it_IT`, `en_GB`, etc.) and format values for third-party mobile applications like **Piper-TTS** on iPhone.
