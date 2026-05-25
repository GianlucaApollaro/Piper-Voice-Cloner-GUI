FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive
ENV TORCH_FLOAT32_MATMUL_PRECISION=medium

# 1. Install System Dependencies (Added espeak-ng)
RUN apt-get update && apt-get install -y \
  git automake autoconf libtool libpcaudio-dev curl build-essential cmake pkg-config \
  python3-pip python3-dev bison flex espeak-ng ffmpeg \
  && ln -sf /usr/bin/python3 /usr/bin/python \
  && rm -rf /var/lib/apt/lists/*

# 2. Install Piper Dependencies & Extensions
# CRITICAL FOR RTX 5070: Use PyTorch Nightly to support sm_120 architecture
# Force uninstall existing torch first to avoid conflicts
RUN pip3 uninstall -y torch torchvision torchaudio || true
# Upgrade pip to ensure it can handle modern wheels and use no-cache to avoid memory issues
# Set timeout and retries to handle unstable connections for large nightly wheels
ENV PIP_DEFAULT_TIMEOUT=1000
ENV PIP_RETRIES=10
RUN pip3 install --upgrade pip
# CRITICAL FIX: "ResolutionImpossible" - Nightly torchvision often lags behind torch updates.
# 1. Install latest TORCH Nightly first.
RUN pip3 install --no-cache-dir --pre --upgrade --force-reinstall torch --index-url https://download.pytorch.org/whl/nightly/cu128
# 2. Install TorchVision/Audio with --no-deps to BYPASS strict version check (force it to use the installed torch)
RUN pip3 install --no-cache-dir --pre --upgrade --force-reinstall --no-deps torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
RUN pip3 install nvidia-nvshmem-cu12 "torchmetrics<0.12" "pytorch-lightning<2.0"
RUN pip3 install piper-phonemize "cython<3" librosa coqpit "numpy<2.0.0" onnx onnxruntime onnxscript tensorboard faster-whisper pydub


# 3. Patch pytorch-lightning to disable weights_only=True default (Security fix for 2.6+)
RUN sed -i 's/return torch.load(f, map_location=map_location)/return torch.load(f, map_location=map_location, weights_only=False)/' /opt/conda/lib/python3.11/site-packages/lightning_fabric/utilities/cloud_io.py

# 4. Pre-download Piper Binary
RUN curl -L -o /tmp/piper.tar.gz https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz \
  && tar -xzf /tmp/piper.tar.gz -C /tmp \
  && mv /tmp/piper/piper /usr/bin/piper \
  && mv /tmp/piper/piper_phonemize /usr/bin/piper_phonemize_bin \
  && mkdir -p /usr/local/piper_libs \
  && find /tmp/piper -name "*.so*" -exec mv {} /usr/local/piper_libs/ \; \
  && mv /tmp/piper/espeak-ng-data /usr/share/espeak-ng-data-piper \
  && ldconfig \
  && rm /tmp/piper.tar.gz

ENV LD_LIBRARY_PATH="/usr/local/piper_libs:$LD_LIBRARY_PATH"

# 5. Clone Piper and Prepare Environment
RUN git clone -q https://github.com/rhasspy/piper.git /piper

WORKDIR /piper/src/python

# 5b. OVERRIDE with Local Code (Bake in local changes)
# OPTIMIZATION: Compile Monotonic Align first to enable Layer Caching
# This allows us to cache the GCC compilation unless monotonic_align code changes.
COPY piper_train/vits/monotonic_align /piper/src/python/piper_train/vits/monotonic_align
RUN pip3 install -e . --no-deps && \
  cd piper_train/vits/monotonic_align && \
  cython core.pyx && \
  gcc -shared -pthread -fPIC -fwrapv -O1 -Wall -fno-strict-aliasing -march=x86-64 -mtune=generic -I/opt/conda/include/python3.11 -o core.so core.c

# Now Copy the rest of the application code
# This will overwrite the source files but PRESERVE the compiled 'core.so'
COPY piper_train /piper/src/python/piper_train

# 7. Apply Patches (Baken in)
# Fix import bug in monotonic_align
RUN sed -i 's/from .monotonic_align.core import maximum_path_c/from .core import maximum_path_c/' /piper/src/python/piper_train/vits/monotonic_align/__init__.py
# Patch Dynamo Export in transforms.py
RUN if [ -f '/piper/src/python/piper_train/vits/transforms.py' ]; then \
  sed -i 's/assert (discriminant >= 0).all(), discriminant/# assert (discriminant >= 0).all(), discriminant/g' /piper/src/python/piper_train/vits/transforms.py; \
  fi
# Patch Export ONNX for Dynamo
RUN if [ -f '/piper/src/python/piper_train/export_onnx.py' ]; then \
  if grep -q 'dynamo=' /piper/src/python/piper_train/export_onnx.py; then \
  sed -i 's/dynamo[[:space:]]*=[[:space:]]*True/dynamo=False/g' /piper/src/python/piper_train/export_onnx.py; \
  else \
  sed -i 's/opset_version/dynamo=False, opset_version/g' /piper/src/python/piper_train/export_onnx.py; \
  fi; \
  fi
