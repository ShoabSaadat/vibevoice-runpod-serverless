# Use RunPod's PyTorch base image with CUDA 12.1
FROM runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone VibeVoice repository
RUN git clone https://github.com/microsoft/VibeVoice.git /app/VibeVoice

# Set working directory to VibeVoice
WORKDIR /app/VibeVoice

# Install VibeVoice dependencies directly (since no setup.py exists)
RUN pip install --no-cache-dir \
    torch>=2.0.0 \
    torchaudio \
    transformers>=4.30.0 \
    accelerate \
    datasets \
    librosa \
    soundfile \
    scipy \
    numpy

# Install additional dependencies for serverless
RUN pip install --no-cache-dir \
    runpod \
    requests \
    numpy \
    torch \
    transformers \
    accelerate \
    flash-attn --no-build-isolation

# Pre-download the VibeVoice-1.5B model (smaller, faster deployment) from Hugging Face
ENV HF_HUB_CACHE=/app/cache
RUN mkdir -p /app/models /app/cache
RUN python -c "from huggingface_hub import snapshot_download; print('Downloading VibeVoice-1.5B model...'); snapshot_download(repo_id='microsoft/VibeVoice-1.5B', local_dir='/app/models/VibeVoice-Large', cache_dir='/app/cache', ignore_patterns=['*.git*', 'README.md']); print('Model downloaded successfully!')"

# Copy the serverless handler
COPY handler.py /app/handler.py

# Set environment variables
ENV MODEL_PATH=/app/models/VibeVoice-Large
ENV PYTHONPATH=/app/VibeVoice:/app
ENV TRANSFORMERS_CACHE=/app/cache
ENV HF_HOME=/app/cache

# Create cache directory
RUN mkdir -p /app/cache

# Set the handler as the entry point
CMD ["python", "/app/handler.py"]
