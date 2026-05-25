import os
import subprocess
import shutil
from .logger import logger
from .docker_manager import DockerManager

class AudioProcessor:
    # We use a standard python image that has torch/whisper or install it?
    # Better: Use a pre-built image with CUDA support and install whisper on fly or use specific image.
    # 'systran/faster-whisper' exists but might be server based.
    # It adds startup time but guarantees compatibility.
    # CRITICAL: Use the main image which has PyTorch Nightly for RTX 5070 support
    from .config_manager import ConfigManager
    TRANSCRIPTION_IMAGE = ConfigManager.DOCKER_IMAGE 
    FFMPEG_IMAGE = "linuxserver/ffmpeg"

    @staticmethod
    def process_dataset(input_dir, output_dir, lang="it"):
        """
        Full pipeline:
        1. Split MP3s in input_dir by silence -> temp_dir
        2. Transcribe temp_dir -> metadata.csv + wavs
        3. Move valid files to output_dir
        """
        temp_dir = os.path.join(output_dir, "temp_split")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # 1. SPLIT ON SILENCE
        logger.info("Step 1: Splitting audio on silence...")
        # We can do this from host if we have ffmpeg? No, use Docker.
        # But complex splitting logic in bash one-liner is hard.
        # Let's use pydub on host if possible? "install_and_run.bat" installs requirements.
        # But we promised automated dependencies.
        # FFmpeg segment muxer can split on silence.
        # simpler: segment by time? No, must not cut words.
        # Use simple python script with pydub inside the same container we use for transcription? 
        # Or just use pydub on host. Pydub needs ffmpeg binary.
        # We can map ffmpeg from docker? No.
        # Let's assume we run the splitting inside the python container too.
        
        # We will create a comprehensive processing script to run inside Docker.
        pass

    @staticmethod
    def run_smart_pipeline(input_dir, output_dir, lang="it", silence_thresh=-32.0, min_silence_len=500, is_relative=False, combine_clips=True, target_dur=10.0, max_dur=15.0, min_dur=0.5, reject_numbers=False, status_callback=None):
        # Version 2.5 - Added Audio Adjustment Parameters
        logger.info("[AudioProcessor] Initializing Smart Pipeline v2.4...")
        
        # Use only the root segment_audio.py relative to this file.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        script_path = os.path.join(project_root, "segment_audio.py")
        if not os.path.exists(script_path):
            logger.error(f"[AudioProcessor] CRITICAL: Could not find root segment_audio.py at {script_path}")
            if status_callback:
                status_callback("Error: root segment_audio.py missing.")
            return False, "Root segment_audio.py missing"

        logger.info(f"[AudioProcessor] Using script: {script_path}")
        
        env_vars = {}
        if "HF_TOKEN" in os.environ:
            env_vars["HF_TOKEN"] = os.environ["HF_TOKEN"]

        is_rel_int = 1 if is_relative else 0
        combine_int = 1 if combine_clips else 0
        reject_int = 1 if reject_numbers else 0
        
        cache_dir = os.path.join(project_root, "models_cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Run Docker with the external script mounted
        return DockerManager.run_container(
            image=AudioProcessor.TRANSCRIPTION_IMAGE,
            command=[
                "/bin/bash", "-c", 
                f"python -u /script.py /input /output {lang} {silence_thresh} {min_silence_len} {is_rel_int} {combine_int} {target_dur} {max_dur} {min_dur} {reject_int}"
            ],
            volumes={
                input_dir: "/input",
                output_dir: "/output",
                script_path: "/script.py", # map the new script here
                cache_dir: "/root/.cache/huggingface"
            },
            env=env_vars,
            gpus=True,
            log_callback=status_callback
        )
