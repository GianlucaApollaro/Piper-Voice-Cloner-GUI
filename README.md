# Piper Voice Cloner (RTX 50-Series & CUDA 12.8 Edition)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.8-green?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue?logo=docker&logoColor=white)](https://www.docker.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-lightgrey?logo=windows&logoColor=white)](https://microsoft.com/)

A modern, user-friendly graphical interface (wxPython) for training, testing, and exporting **Piper VITS** voice models. This package is optimized out-of-the-box for **NVIDIA RTX 50-series (e.g., RTX 5070)** and newer graphics cards, featuring native CUDA 12.8/PyTorch 2.5+ Docker backends, local model caching, and custom voice post-processing tools.

---

## 🌟 Key Features & New Additions

### 🚀 Performance & Caching
* **Local Faster-Whisper Cache**: Mounts a local `models_cache` folder directly into the Docker containers. This prevents redownloading the 3GB Whisper `large-v3` model, drastically speeding up dataset transcription and translation starts.
* **Auto GPU Acceleration Setup**: Detects NVIDIA RTX 20/30/40/50 series cards and configures optimal batch sizes and mixed-precision (16-bit) settings dynamically.

### 🎙️ Dataset Ingestion & Translation
* **Prosody-First Audio Splitting**: Automated splitting logic prioritizing breathing pauses and sentence structure (gaps >300ms favored, gaps <150ms penalized) to ensure natural speech flow (2-15s clips).
* **Zero-Shot Audio Translation**: Whisper-based translation tab utilizing zero-shot target language conditioning. Translate speech from any language directly to Italian, Spanish, French, German, or English.

### ✏️ Correction Studio
* **Keyboard Hotkeys**: Streamlined workflow with explicit keyboard controls:
  * **F3**: Search segments by text or file ID.
  * **F4**: Go to Previous segment.
  * **F5**: Listen to the segment audio (asynchronously).
  * **F6**: Go to Next segment.
  * **Ctrl+S**: Save edits to disk (auto-saves on segment navigation).
* **Concurrent Metadata Operations**: Safely updates transcripts while background ingestion processes are running.

### 📱 Mobile Compatibility & Export
* **Piper-TTS iOS/Mobile Enrichment**: During model export, the system automatically post-processes and enriches the generated `{model}.onnx.json` config file:
  * Upgrades audio quality labels (e.g., changing internal `"dataset"` value to `"medium"`).
  * Fills in missing regional metadata (native language name, English language family, region code, and country name).
  * Makes exported models directly compatible with mobile readers (such as **Piper-TTS** on iPhone).

---

## 📋 System Requirements

* **OS**: Windows 10 or Windows 11.
* **GPU**: NVIDIA Graphics Card (RTX 20, 30, 40, or 50 series).
* **Software**: 
  * Docker Desktop (with WSL2 backend enabled).
  * Latest NVIDIA Game Ready or Studio Drivers.

---

## ⚙️ Installation & First-Time Setup

1. **Clone/Copy Project Folder**: Copy the repository contents into a directory (e.g., `C:\piper_ui` or `J:\piper_ui`). **Do not use folders containing spaces in their paths.**
2. **Build the Container Image**: Double-click `build_image.bat`.
   > [!NOTE]
   > This script downloads dependencies (PyTorch Nightly cu128, CUDA, etc.) and compiles the specialized image `piper-cuda12.8:latest`. The download size is approximately 8–10 GB. Please wait until the terminal says "Press any key to continue" or closes.
3. **Setup Host Environment**: Double-click `install.bat` to create the virtual environment and install UI dependencies on the Windows host.

---

## 🚀 Running the App

1. Double-click `install_and_run.bat`.
2. The graphical interface will open.
3. **Change Language**: You can switch between **English** and **Italiano** using the **Language** menu at the top left (requires a restart to apply).

---

## 📖 Step-by-Step Workflow Guide

### Step 1: Prepare the Dataset (Dataset Tab)
1. **Audio Source**: Select the folder containing your raw recordings (`.wav` or `.mp3`).
2. **Language Code**: Enter the language code for your dataset (e.g., `it` or `en`).
3. **Silence Thresholds**: Adjust the dBFS offset and minimum silence lengths if desired.
4. **Reject Numbers**: (Enabled by default) Automatically filters out audio lines containing numbers to prevent Piper pronunciation errors.
5. **Start Processing**: Click **Start Processing**. The app splits the files and transcribes them using Whisper.
   * *Output*: A new folder called `processed/` is created inside your source folder, containing the `.wav` files and a clean `metadata.csv`.
6. **Merge external data**: You can merge an external dataset folder into your active dataset by clicking **Merge External Dataset**.

### Step 2: Review Transcripts (Correction Tab)
1. Select the `processed` folder path.
2. Navigate clips using **Previous (F4)** and **Next (F6)**.
3. Listen to the audio with **Listen (F5)** and modify incorrect words.
4. Save edits using **Ctrl+S** (navigating also triggers auto-save).

### Step 3: Piper Preprocessing (Preprocess Tab)
1. Set the **Dataset Folder** to the `processed/` folder path.
2. Select the specific dialect code (e.g., `it`, `en-us`, `es`, `fr`, `de`).
3. Adjust the number of **Workers (Threads)** based on your CPU cores.
4. Click **Preprocess Dataset** to format text and audio features for training.

### Step 4: Training the Model (Train Tab)
1. Set the training parameters:
   * **Batch Size**: 8–16 recommended for RTX 5070 (12GB VRAM).
   * **Validation Split**: Set to `0.05` or `0.10` to keep a percentage of testing data.
   * **Precision**: Set to `16` (Mixed Precision) for maximum speed and lower VRAM usage.
   * **Auto-Stop (Patience)**: Stops training automatically if the voice stops improving after N epochs.
   * **Stop at Overtraining**: Actively monitors validation loss rather than training loss.
2. Click **Start Training**. You can monitor the metrics stream in the log pane.
3. Click **Stop Training** (or press **Ctrl+K**) to pause/save checkpoints manually.

### Step 5: Exporting to ONNX (Export Tab)
1. Select the checkpoint file (`.ckpt`) located inside your dataset's `lightning_logs` directory.
2. Click **Export via ONNX**.
   * *Output*: A `model.onnx` and `model.onnx.json` are created under `exported_model/`.
   * **Mobile Compatibility**: The JSON file is automatically processed to include standard regional codes (`en_GB`, `it_IT`, etc.) and quality keys (`medium`), making it ready for mobile applications.

### Step 6: Test Voice (Test Tab)
1. Load your exported `model.onnx` file.
2. Write text or load a document.
3. Click **Generate Audio** and click **Play 🔊** to listen.
4. Save the generated voice as a `.wav` file by clicking **Save Audio...**.

---

## 🧹 Docker & Disk Maintenance

Because Docker and WSL2 virtual disks grow over time on Windows, follow these maintenance steps to reclaim space:

### Cleaning Unused Docker Data
Run these commands in PowerShell or Command Prompt:
1. Remove stopped containers:
   ```powershell
   docker container prune
   ```
2. Remove dangling images:
   ```powershell
   docker image prune
   ```
3. **Reclaim massive space** by removing Docker's builder cache:
   ```powershell
   docker builder prune --all
   ```

### Shrinking the WSL2 Virtual Disk (ext4.vhdx)
1. Quit Docker Desktop (right-click tray icon -> "Quit Docker Desktop").
2. Open PowerShell as **Administrator** and shut down WSL:
   ```powershell
   wsl --shutdown
   ```
3. Open Diskpart:
   ```powershell
   diskpart
   ```
4. Select your virtual disk file (replace with your Windows username):
   ```diskpart
   select vdisk file="C:\Users\YOUR_USERNAME\AppData\Local\Docker\wsl\data\ext4.vhdx"
   ```
5. Compact and exit:
   ```diskpart
   compact vdisk
   exit
   ```
6. Relaunch Docker Desktop.

---

## 📦 Packaging & Sharing

Before zipping this project folder to share it with others or backup, **delete** these temporary directories to protect your privacy and reduce the archive size by several gigabytes:
* `venv/` (your local python environment)
* `__pycache__/`
* `dataset/` / `processed/` (audio datasets and recordings)
* `lightning_logs/` (training checkpoints and logs)
* `exported_model/`
* `checkpoints/`
* `.git/` (if present)
