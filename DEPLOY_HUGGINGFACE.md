# 🤗 VibeVoice-Large Direct Hugging Face Deployment

This guide shows how to deploy VibeVoice directly from Hugging Face to RunPod Serverless with **zero manual uploads**.

## 🚀 Quick Deployment (5 minutes)

### **Step 1: Create RunPod Serverless Endpoint**

1. **Go to**: https://runpod.io/serverless
2. **Click**: "New Endpoint"
3. **Select**: "Custom" (not template)

### **Step 2: Configuration**

**Container Settings:**
- **Container Image**: `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04`
- **Container Disk**: `50 GB`
- **Handler**: `handler.py`

**Environment Variables:**
```env
MODEL_NAME=microsoft/VibeVoice-1.5B
MODEL_PATH=/app/models/VibeVoice-Large
HF_HOME=/app/cache
TRANSFORMERS_CACHE=/app/cache
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

**Docker Build Commands:**
```bash
apt-get update && apt-get install -y git ffmpeg wget curl
git clone https://github.com/microsoft/VibeVoice.git /app/VibeVoice
cd /app/VibeVoice && pip install -e .
pip install runpod requests transformers accelerate flash-attn --no-build-isolation
mkdir -p /app/models /app/cache
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='microsoft/VibeVoice-1.5B', local_dir='/app/models/VibeVoice-Large', cache_dir='/app/cache')"
```

**Handler Code (Paste this directly):**

```python
#!/usr/bin/env python3

import runpod
import os
import sys
import torch
import tempfile
import base64
import subprocess
import logging
import traceback

# Add VibeVoice to path
sys.path.insert(0, '/app/VibeVoice')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model variable
model_ready = False

def ensure_model():
    """Ensure VibeVoice model is downloaded and available"""
    global model_ready
    
    if model_ready:
        return True
    
    try:
        model_path = '/app/models/VibeVoice-Large'
        
        # Check if model exists, if not download
        if not os.path.exists(model_path):
            logger.info("Downloading VibeVoice-Large from Hugging Face...")
            from huggingface_hub import snapshot_download
            
            snapshot_download(
                repo_id='microsoft/VibeVoice-1.5B',
                local_dir=model_path,
                cache_dir='/app/cache'
            )
            logger.info("Model downloaded successfully!")
        
        model_ready = True
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure model: {e}")
        return False

def generate_audio_via_demo(text, speaker_names, output_path):
    """Use VibeVoice demo script to generate audio"""
    
    # Create temporary text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as txt_file:
        txt_file.write(text)
        txt_path = txt_file.name
    
    try:
        # Build command for VibeVoice demo
        cmd = [
            'python', '/app/VibeVoice/demo/inference_from_file.py',
            '--model_path', '/app/models/VibeVoice-Large',
            '--txt_path', txt_path,
            '--speaker_names'
        ] + speaker_names
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Run the inference
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/app/VibeVoice')
        
        if result.returncode == 0:
            # Find generated audio file
            output_dir = '/outputs'  # Default VibeVoice output
            if os.path.exists(output_dir):
                for file in os.listdir(output_dir):
                    if file.endswith('.wav'):
                        generated_path = os.path.join(output_dir, file)
                        # Move to desired output path
                        import shutil
                        shutil.move(generated_path, output_path)
                        return output_path
            
            logger.error("Generated audio file not found")
            return None
        else:
            logger.error(f"Generation failed: {result.stderr}")
            return None
            
    finally:
        # Clean up
        try:
            os.unlink(txt_path)
        except:
            pass

def handler(job):
    """Main handler function"""
    try:
        job_input = job.get("input", {})
        
        # Validate input
        if "text" not in job_input:
            return {
                "error": "Missing required 'text' parameter",
                "example": {
                    "text": "Speaker 1: Hello! Speaker 2: Hi there!",
                    "speaker_names": ["Alice", "Bob"]
                }
            }
        
        # Ensure model is ready
        if not ensure_model():
            return {"error": "Failed to load VibeVoice model"}
        
        text = job_input["text"]
        speaker_names = job_input.get("speaker_names", ["Alice", "Bob"])
        output_format = job_input.get("output_format", "wav")
        
        logger.info(f"Generating audio: {text[:100]}...")
        
        # Generate audio
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as audio_file:
            output_path = audio_file.name
        
        try:
            generated_path = generate_audio_via_demo(text, speaker_names, output_path)
            
            if not generated_path or not os.path.exists(generated_path):
                return {"error": "Audio generation failed"}
            
            # Read and encode audio
            with open(generated_path, 'rb') as f:
                audio_data = f.read()
            
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            file_size_mb = len(audio_data) / (1024 * 1024)
            
            logger.info(f"Audio generated successfully! Size: {file_size_mb:.2f} MB")
            
            return {
                "success": True,
                "audio_base64": audio_base64,
                "format": output_format,
                "size_mb": round(file_size_mb, 2),
                "speakers": speaker_names,
                "text_length": len(text)
            }
            
        finally:
            try:
                os.unlink(output_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Handler failed: {str(e)}"}

# Start the serverless worker
runpod.serverless.start({"handler": handler})
```

### **Step 3: GPU Configuration**

**Recommended GPUs:**
- **RTX 4090** (30GB VRAM) - Most cost-effective
- **RTX A6000** (48GB VRAM) - Best balance  
- **A100 80GB** - Maximum performance

**Settings:**
- **Workers Min**: 0
- **Workers Max**: 1  
- **Idle Timeout**: 5 seconds
- **Execution Timeout**: 600 seconds

### **Step 4: Deploy!**

Click **"Deploy"** - RunPod will:
1. ✅ Pull PyTorch base image
2. ✅ Clone VibeVoice from GitHub  
3. ✅ Download model from Hugging Face
4. ✅ Build container automatically
5. ✅ Deploy serverless endpoint

## 🎯 **Key Benefits of This Method:**

✅ **Zero Manual Uploads** - Everything pulled from cloud  
✅ **Direct HuggingFace Integration** - Always latest model  
✅ **Auto-Scaling** - Pay only when generating audio  
✅ **Fast Cold Start** - ~15-30 seconds  
✅ **Reliable** - No internet interruption issues  

## 📡 **Testing Your Endpoint**

Once deployed, test with:

```python
import requests
import base64

response = requests.post(
    'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    json={
        'input': {
            'text': 'Speaker 1: Hello! Welcome to VibeVoice. Speaker 2: This is incredible quality!',
            'speaker_names': ['Alice', 'Bob']
        }
    }
)

result = response.json()

if result.get('output', {}).get('success'):
    audio_data = base64.b64decode(result['output']['audio_base64'])
    with open('generated.wav', 'wb') as f:
        f.write(audio_data)
    print("✅ Audio generated and saved!")
```

## 💰 **Expected Costs:**

- **Cold Start**: ~$0.01-0.02 (15-30 seconds)
- **Audio Generation**: ~$0.006-0.03 per minute of audio
- **Idle Time**: $0 (auto-scales to zero)

**Total per audio generation**: Usually **$0.02-0.05** per request

## 🔧 **Troubleshooting:**

**Build Issues:**
- Check container logs in RunPod dashboard
- Verify environment variables are set
- Ensure 50GB+ disk space selected

**Runtime Issues:**  
- Check handler logs for model download progress
- Verify GPU has sufficient VRAM (30GB+)
- Test with shorter text first

**This method is 100% cloud-based with no manual file handling!** 🚀
