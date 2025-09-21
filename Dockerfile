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

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Install additional dependencies for serverless
RUN pip install --no-cache-dir \
    runpod \
    requests \
    numpy \
    torch \
    transformers \
    accelerate \
    flash-attn --no-build-isolation

# Pre-download the VibeVoice-Large model (9.34B params) from Hugging Face
ENV HF_HUB_CACHE=/app/cache
RUN mkdir -p /app/models /app/cache
RUN python -c "from huggingface_hub import snapshot_download; print('Downloading VibeVoice-Large model...'); snapshot_download(repo_id='microsoft/VibeVoice-1.5B', local_dir='/app/models/VibeVoice-Large', cache_dir='/app/cache', ignore_patterns=['*.git*', 'README.md']); print('Model downloaded successfully!')"

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
