import os
import json
import subprocess

class ConfigManager:
    # Use modern image with native RTX 5070 support (PyTorch 2.5.1, CUDA 12.4)
    # Updated to local custom image
    DOCKER_IMAGE = "piper-cuda12.8:latest"
    
    @staticmethod
    def detect_gpu_settings():
        """
        Detect NVIDIA GPU and return optimal settings (batch size, etc.)
        Returns a dict with 'batch_size' and 'gpu_name'.
        """
        default_settings = {"batch_size": 4, "gpu_name": "Unknown/CPU"}
        
        try:
            # Run nvidia-smi to get GPU info
            # We use noheader and csv format to get a clean string
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                check=True
            )
            
            gpu_name = result.stdout.strip()
            settings = {"batch_size": 4, "gpu_name": gpu_name}
            
            # Simple heuristic based on known strong cards
            if any(x in gpu_name for x in ['RTX 50', '5070', '5080', '5090']):
                settings["batch_size"] = 8
            elif any(x in gpu_name for x in ['RTX 40', '4070', '4080', '4090']):
                settings["batch_size"] = 8
            elif any(x in gpu_name for x in ['RTX 30', '3080', '3090']):
                settings["batch_size"] = 6
            elif any(x in gpu_name for x in ['RTX 30', '3060', '3070']): # 3070 usually fine with 8 but safer 6
                settings["batch_size"] = 4
            elif 'RTX 20' in gpu_name:
                settings["batch_size"] = 4
                
            return settings
            
        except (subprocess.CalledProcessError, FileNotFoundError):
             # nvidia-smi missing or failed
             print("GPU Detection failed or no NVIDIA GPU found.")
             return default_settings
        except Exception as e:
            print(f"Error checking GPU: {e}")
            return default_settings

    # Preset Checkpoints Configuration
    # Format: "Label": {"url": "huggingface_download_url", "file": "filename.ckpt"}
    PRESET_CHECKPOINTS = {
        "it_IT-leonardo-medium (Male) ⭐": {
            "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Leonardo/leonardo-epoch=2024-step=996300.ckpt",
            "file": "leonardo-epoch=2024-step=996300.ckpt"
        },
        "it_IT-aurora-medium (Female)": {
            "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Aurora/epoch=2093-step=498372.ckpt",
            "file": "epoch=2093-step=498372.ckpt"
        },
        "it_IT-giorgio-medium (Male)": {
            "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Giorgio/giorgio-epoch=5028-step=1098436.ckpt",
            "file": "giorgio-epoch=5028-step=1098436.ckpt"
        }
    }

    # Preset Voices for Testing (ONNX models)
    # Format: "Label": {"url": "onnx_url", "config_url": "json_url", "file": "filename.onnx", "config_file": "filename.onnx.json"}
    PRESET_VOICES = {
        # ITALIANO
        "🇮🇹 Leonardo (Maschile) ⭐": {
            "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Leonardo/leonardo-epoch=2024-step=996300.onnx",
            "config_url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Leonardo/leonardo-epoch=2024-step=996300.json",
            "file": "leonardo-epoch=2024-step=996300.onnx",
            "config_file": "leonardo-epoch=2024-step=996300.onnx.json"  # Piper expects .onnx.json
        },
        "🇮🇹 Aurora (Femminile)": {
            "url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Aurora/it_IT-aurora-medium.onnx",
            "config_url": "https://huggingface.co/kirys79/piper_italiano/resolve/main/Aurora/it_IT-aurora-medium.onnx.json",
            "file": "it_IT-aurora-medium.onnx",
            "config_file": "it_IT-aurora-medium.onnx.json"
        },
        "🇮🇹 Riccardo (Maschile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx.json",
            "file": "it_IT-riccardo-x_low.onnx",
            "config_file": "it_IT-riccardo-x_low.onnx.json"
        },
        
        # TEDESCO
        "🇩🇪 Thorsten High (Maschile) ⭐": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx.json",
            "file": "de_DE-thorsten-high.onnx",
            "config_file": "de_DE-thorsten-high.onnx.json"
        },
        "🇩🇪 Thorsten Medium (Maschile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json",
            "file": "de_DE-thorsten-medium.onnx",
            "config_file": "de_DE-thorsten-medium.onnx.json"
        },
        
        # FRANCESE
        "🇫🇷 Tom (Maschile) ⭐": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx.json",
            "file": "fr_FR-tom-medium.onnx",
            "config_file": "fr_FR-tom-medium.onnx.json"
        },
        "🇫🇷 Siwis (Maschile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json",
            "file": "fr_FR-siwis-medium.onnx",
            "config_file": "fr_FR-siwis-medium.onnx.json"
        },
        
        # SPAGNOLO
        "🇪🇸 Daniela High (Femminile) ⭐": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_AR/daniela/high/es_AR-daniela-high.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_AR/daniela/high/es_AR-daniela-high.onnx.json",
            "file": "es_AR-daniela-high.onnx",
            "config_file": "es_AR-daniela-high.onnx.json"
        },
        "🇪🇸 Davefx (Maschile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
            "file": "es_ES-davefx-medium.onnx",
            "config_file": "es_ES-davefx-medium.onnx.json"
        },
        
        # INGLESE (US)
        "🇺🇸 Ryan High (Maschile) ⭐": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx.json",
            "file": "en_US-ryan-high.onnx",
            "config_file": "en_US-ryan-high.onnx.json"
        },
        "🇺🇸 Lessac High (Femminile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/high/en_US-lessac-high.onnx.json",
            "file": "en_US-lessac-high.onnx",
            "config_file": "en_US-lessac-high.onnx.json"
        },
        "🇺🇸 Amy Medium (Femminile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
            "file": "en_US-amy-medium.onnx",
            "config_file": "en_US-amy-medium.onnx.json"
        },
        
        # INGLESE (UK)
        "🇬🇧 Cori High (Femminile) ⭐": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/cori/high/en_GB-cori-high.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/cori/high/en_GB-cori-high.onnx.json",
            "file": "en_GB-cori-high.onnx",
            "config_file": "en_GB-cori-high.onnx.json"
        },
        "🇬🇧 Alan Medium (Maschile)": {
            "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
            "config_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json",
            "file": "en_GB-alan-medium.onnx",
            "config_file": "en_GB-alan-medium.onnx.json"
        }
    }

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        """Load config from file or create default."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        return self._create_default_config()

    def _create_default_config(self):
        """Create default configuration."""
        return {
            "dataset_path": "",
            "language": "it",
            "docker_image": self.DOCKER_IMAGE,
            "batch_size": 8,
            "max_epochs": 10000,
            "quality": "medium",
            "precision": "32",
            "validation_split": 0.0,
            "base_model_checkpoint": None,
            "use_single_speaker": False
        }

    def save_config(self, config):
        """Save configuration to file."""
        self.config = config
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def get_docker_run_command(self, use_gpu=True):
        """Generate the docker run command."""
        cmd = ["docker", "run", "--rm", "-it"]
        if use_gpu:
            cmd.extend(["--gpus", "all"])
            
        cmd.extend([
            "-v", f"{os.getcwd()}:/app",
            self.config.get("docker_image", self.DOCKER_IMAGE)
        ])
        return cmd

    @staticmethod
    def _get_setup_script():
        """
        Get the setup script.
        CRITICAL: We MUST use PyTorch Nightly cu126 (CUDA 12.6) for RTX 5070 (sm_120) support.
        The Docker image might have cu124, so we force an upgrade/reinstall at runtime if needed.
        """
        return (
            "export DEBIAN_FRONTEND=noninteractive; "
            "export TORCH_FLOAT32_MATMUL_PRECISION=medium; "
            # Ensure /piper repo exists
            "if [ ! -d '/piper/src/python' ]; then "
            "  echo 'Cloning Piper...'; "
            "  git clone -q https://github.com/rhasspy/piper.git /piper; "
            "  cd /piper/src/python; "
            "  pip3 install -e . --no-deps; "
            "  cd piper_train/vits/monotonic_align; "
            "  cython core.pyx; "
            "  gcc -shared -pthread -fPIC -fwrapv -O1 -Wall -fno-strict-aliasing -march=x86-64 -mtune=generic -I/opt/conda/include/python3.11 -o core.so core.c; "
            "  cd /piper/src/python; "
            "  sed -i 's/from .monotonic_align.core import maximum_path_c/from .core import maximum_path_c/' piper_train/vits/monotonic_align/__init__.py; "
            "fi; "
            # PATCH: Fix Dynamo Export Error in transforms.py (GuardOnDataDependentSymNode)
            "if [ -f '/piper/src/python/piper_train/vits/transforms.py' ]; then "
            "  sed -i 's/assert (discriminant >= 0).all(), discriminant/# assert (discriminant >= 0).all(), discriminant/g' /piper/src/python/piper_train/vits/transforms.py; "
            "fi; "
            # PATCH: Disable Dynamo for ONNX Export - ROBUST
            "if [ -f '/piper/src/python/piper_train/export_onnx.py' ]; then "
            "  if grep -q 'dynamo=' /piper/src/python/piper_train/export_onnx.py; then "
            "    sed -i 's/dynamo[[:space:]]*=[[:space:]]*True/dynamo=False/g' /piper/src/python/piper_train/export_onnx.py; "
            "  else "
            "    sed -i 's/opset_version/dynamo=False, opset_version/g' /piper/src/python/piper_train/export_onnx.py; "
            "  fi; "
            "fi; "
            # PATCH: Fix Batched ValueError (n must be at least one)
            # This happens when num_workers > num_utterances, resulting in batch_size=0.
            # We patch the call to batched() to ensure n=max(1, batch_size)
            "if [ -f '/piper/src/python/piper_train/preprocess.py' ]; then "
            # Look for: for utt_batch in batched(utterances, len(utterances) // args.max_workers):
            # Replace with: for utt_batch in batched(utterances, max(1, len(utterances) // args.max_workers)):
            # Patch the ACTUAL assignment found in logs: batch_size = int(num_utterances / (args.max_workers * 2))
            # We wrap the calculation in max(1, ...)
            "  sed -i 's/batch_size = int(num_utterances \/ (args.max_workers \* 2))/batch_size = max(1, int(num_utterances \/ (args.max_workers \* 2)))/g' /piper/src/python/piper_train/preprocess.py; "
            "fi; "
            # CRITICAL FIX: Upgrade to cu128 & Clean Install Dependencies
            "echo 'Checking PyTorch Version for RTX 5070...'; "
            "export TORCH_CUDA_ARCH_LIST=; "
            # OPTIMIZATION: Check if environment is already baked (from updated Dockerfile)
            # Use 'pip list' to check for nightly/dev version to avoid 'import torch' triggering GPU init crashes.
            "(pip3 list | grep '^torch ' | grep 'dev' > /dev/null) && "
            "echo '--- Environment already optimized (Baked Image Detected via PIP) ---' || "
            "( "
            "echo '--- Legacy/Stock Image Detected: Starting Scorched Earth Fix ---'; "
            # 1. Uninstall existing packages using Python for robustness
            "python3 -c \"import subprocess; installed = [line.split()[0] for line in subprocess.check_output(['pip3', 'list']).decode().split('\\n') if line and (line.startswith('nvidia-') or line.startswith('triton') or line.startswith('torch'))]; print(f'Uninstalling: {installed}'); subprocess.run(['pip3', 'uninstall', '-y'] + installed) if installed else None\"; "
            # 2. Fresh Install of Torch cu128
            "pip3 install --default-timeout=1000 --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128; "
            # 3. Install missing nvshmem
            "pip3 install --default-timeout=1000 nvidia-nvshmem-cu12; "
            # 4. RESTORE ORPHANED DEPENDENCIES
            "echo '--- Restoring Orphaned Dependencies ---'; "
            "pip3 install --no-cache-dir \"torchmetrics<0.12\"; "
            "pip3 install --no-cache-dir \"pytorch-lightning<2.0\"; "
            "pip3 install --no-cache-dir onnx onnxruntime onnxscript; "
            "); "
            
            # 5. Robust Symlink for nvshmem (Always run this, just in case path varies)
            "SHMEM_LIB=$(find /opt/conda/lib/python3.11/site-packages -name 'libnvshmem_host.so*' | head -n 1); "
            "if [ -n \"$SHMEM_LIB\" ]; then "
            "  echo \"Found libnvshmem at $SHMEM_LIB, linking...\"; "
            "  ln -sf $SHMEM_LIB /usr/lib/libnvshmem_host.so.3; "
            "  ln -sf $SHMEM_LIB /usr/lib/libnvshmem_host.so; "
            "  export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(dirname $SHMEM_LIB); "
            "else "
            "  echo 'WARNING: libnvshmem still not found after install'; "
            "fi; "
            
            # 6. INFERENCE DEPENDENCIES (Runtime)
            # Ensure piper-tts and espeak-ng are installed for the Test tab
            # Ensure tensorboard is installed for Training (Validation Audio Logging)
            # Ensure piper-tts and espeak-ng are installed for the Test tab
            # Ensure tensorboard is installed for Training (Validation Audio Logging)
            "if ! dpkg -l | grep -q 'espeak-ng-data'; then "
            "  echo 'Installing espeak-ng and data (required for inference/preprocessing)...'; "
            "  apt-get update && apt-get install -y espeak-ng espeak-ng-data; "
            "fi; "
            # FIX: Check for piper BINARY (C++) instead of python package to prevent shadowing/conflicts
            "if ! which piper > /dev/null; then "
            "  echo 'Installing piper-tts (fallback)...'; "
            "  pip3 install piper-tts; "
            "fi; "
            "python3 -c 'import tensorboard' 2>/dev/null || (echo 'Installing tensorboard...' && pip3 install tensorboard); "

            "echo '--- VERIFICATION ---'; "
            "python3 -c 'import torch; print(\"Torch Version:\", torch.__version__); print(\"CUDA Available:\", torch.cuda.is_available())'; "
        )

    @staticmethod
    def download_checkpoint(checkpoint_entry, output_folder):
        """
        Downloads the checkpoint file from URL to output_folder if not exists.
        Returns the absolute path to the file.
        """
        import requests
        import os
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
        file_path = os.path.join(output_folder, checkpoint_entry["file"])
        
        if not os.path.exists(file_path):
            print(f"Downloading checkpoint to {file_path}...")
            # Let exceptions propagate to the UI for visibility
            response = requests.get(checkpoint_entry["url"], stream=True, timeout=30) 
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Download complete.")

        return file_path

    @staticmethod
    def get_preprocess_command(language_code, dataset_format, sample_rate=22050, use_single_speaker=False, max_workers=1):
        """
        Generates the command for preprocessing.
        """
        setup = ConfigManager._get_setup_script()
        
        # Espeak expects hyphens (e.g. en-us) and sometimes base codes (e.g. it, not it-it)
        sanitized_lang = language_code.replace("_", "-")
        
        # Specific overrides for espeak-ng common languages
        # Espeak often uses 2-letter codes for the primary dialect
        ESPEAK_ALIASES = {
            "it-IT": "it",
            "fr-FR": "fr", 
            "es-ES": "es",
            "de-DE": "de",
            "en-US": "en-us", # Explicitly keep these
            "en-GB": "en-gb",
            "pt-BR": "pt-br",
            "es-MX": "es-mx"
        }
        
        if sanitized_lang in ESPEAK_ALIASES:
             sanitized_lang = ESPEAK_ALIASES[sanitized_lang]
        
        single_speaker_flag = "--single-speaker" if use_single_speaker else ""
        
        cmd = (
            f"python3 -m piper_train.preprocess "
            f"--language {sanitized_lang} "
            f"--input-dir /dataset "
            f"--output-dir /dataset "
            f"--dataset-format {dataset_format} "
            f"--sample-rate {sample_rate} "
            f"{single_speaker_flag} "
            f"--max-workers {max_workers}"
        )
        return ["/bin/bash", "-c", setup + cmd]

    @staticmethod
    def get_train_command(batch_size, validation_split=0.05, quality="medium", precision=32, max_epochs=10000, resume_checkpoint=None, checkpoint_epochs=1, learning_rate=0.0001, num_workers=4, accumulate_grad_batches=1):
        """
        Generates the command for training.
        """
        setup = ConfigManager._get_setup_script()
        # We need to ensure we run from the correct directory or python path
        cmd = (
            f"python3 -m piper_train "
            f"--dataset-dir /dataset "
            f"--dataset-config /dataset/dataset_safe.jsonl "
            f"--accelerator gpu "
            f"--devices 1 "
            f"--batch-size {batch_size} "
            f"--validation-split {validation_split} "
            f"--precision {precision} "
            f"--max_epochs {max_epochs} "
            f"--checkpoint-epochs {checkpoint_epochs} "
            f"--learning-rate {learning_rate} "
            f"--num-workers {num_workers} "
            f"--accumulate_grad_batches {accumulate_grad_batches} "
            f"--log_every_n_steps 10"
        )

        if resume_checkpoint:
            cmd += f" --resume_from_checkpoint {resume_checkpoint}"

        return ["/bin/bash", "-c", setup + cmd]

    @staticmethod
    def get_export_command(checkpoint_path, model_name="model", config_path="/dataset/config.json"):
        """
        Generates the command to export the checkpoint to ONNX.
        """
        setup = ConfigManager._get_setup_script()
        cmd = (
            f"mkdir -p /dataset/exported_model && "
            f"python3 -m piper_train.export_onnx "
            f"{checkpoint_path} "
            f"/dataset/exported_model/{model_name}.onnx && "
            f"cp {config_path} /dataset/exported_model/{model_name}.onnx.json && "
            f"echo '--- DIRECTORY LISTING ---' && "
            f"ls -la /dataset/exported_model && "
            f"echo '--- EXPORT DONE ---'"
        )
        return ["/bin/bash", "-c", setup + cmd]
