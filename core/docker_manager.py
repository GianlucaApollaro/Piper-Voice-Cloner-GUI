import subprocess
import shutil
from .logger import logger
from .translation_manager import tr

class DockerManager:
    @staticmethod
    def is_docker_installed():
        """Check if docker is installed and reachable."""
        if not shutil.which("docker"):
            return False
        try:
            subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def image_exists(image_name):
        """Check if a docker image exists locally."""
        if not DockerManager.is_docker_installed():
            return False
        try:
            # Clean tab in image name if present (e.g. name:tag)
            cmd = ["docker", "inspect", "--type=image", image_name]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def build_image(dockerfile_path, image_name, log_callback=None):
        """Build a docker image from a Dockerfile."""
        if not DockerManager.is_docker_installed():
            return False, tr("err_docker_not_installed")
            
        cmd = ["docker", "build", "-t", image_name, "-f", dockerfile_path, "."]
        logger.info("Building image: %s", " ".join(cmd))
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            output_lines = []
            for line in process.stdout:
                line_clean = line.strip()
                if line_clean:
                    output_lines.append(line_clean)
                    if log_callback:
                        log_callback(line_clean)
            
            process.wait()
            
            if process.returncode == 0:
                return True, "Build successful"
            else:
                return False, "\n".join(output_lines)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def check_gpu_support():
        """
        Check if GPU is available in Docker.
        Runs a quick nvidia-smi container.
        """
        if not DockerManager.is_docker_installed():
            return False, tr("err_docker_not_installed")
        
        # We use a standard nvidia image for the check, not our custom one necessarily,
        # but to be safe we can use the base image of our custom one if we knew it,
        # or just a standard small one.
        cmd = [
            "docker", "run", "--rm", "--gpus", "all",
            "nvidia/cuda:12.4.1-base-ubuntu22.04", # Updated to 12.4 to match our target
            "nvidia-smi"
        ]
        
        logger.info("Checking GPU support with command: %s", " ".join(cmd))
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    @staticmethod
    def run_container(image, command, volumes=None, env=None, gpus=False, detach=False, tty=False, log_callback=None):
        """
        Run a docker container.
        volumes: dict of {local_path: container_path}
        env: dict of {key: value} environment variables
        log_callback: function to call with each line of output
        """
        cmd = ["docker", "run", "--rm", "--shm-size=2gb"]
        if gpus:
            cmd.extend(["--gpus", "all"])
            
        if env:
            for k, v in env.items():
                if v is not None:
                    cmd.extend(["-e", f"{k}={v}"])
        
        if tty:
            cmd.append("-t")
        
        if volumes:
            for local, container in volumes.items():
                cmd.extend(["-v", f"{local}:{container}"])
        
        if detach:
            cmd.append("-d")
            
        cmd.append(image)
        if isinstance(command, list):
            cmd.extend(command)
        else:
            cmd.append(command)
            
        logger.info("Running container: %s", " ".join(cmd))
        
        if detach:
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
            except Exception as e:
                return False, str(e)
        
        # Collaborative streaming for foreground containers
        try:
            # Merge stdout and stderr for simplicity in logging
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1, 
                encoding='utf-8',
                errors='replace'
            )
            
            output_lines = []
            
            # Stream output
            for line in process.stdout:
                line_clean = line.strip()
                if line_clean:
                    output_lines.append(line_clean)
                    if log_callback:
                        log_callback(line_clean)
                    # Also log to file if needed, but callback handles UI
            
            process.wait()
            
            full_log = "\n".join(output_lines)
            if process.returncode == 0:
                return True, full_log
            else:
                return False, full_log
                
        except Exception as e:
            return False, str(e)

    @staticmethod
    def cleanup_stale_containers(image_name):
        """Find and stop any running containers from previous sessions."""
        if not DockerManager.is_docker_installed():
            return
            
        logger.info(f"Checking for stale containers of image: {image_name}")
        try:
            # Find
            cmd_find = ["docker", "ps", "-q", "--filter", f"ancestor={image_name}"]
            result = subprocess.run(cmd_find, stdout=subprocess.PIPE, text=True)
            ids = result.stdout.strip().split()
            
            if ids:
                logger.info(f"Found {len(ids)} stale containers. Stopping...")
                # Stop
                cmd_stop = ["docker", "stop"] + ids
                subprocess.run(cmd_stop, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info("Stale containers stopped.")
            else:
                logger.info("No stale containers found.")
                
        except Exception as e:
            logger.error(f"Error cleaning up containers: {e}")
