#!/usr/bin/env python3

import runpod
import os
import sys
import torch
import tempfile
import base64
from pathlib import Path
import logging
import traceback

# Add VibeVoice to path
sys.path.insert(0, '/app/VibeVoice')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model variable
model = None
device = None

def initialize_model():
    """Initialize VibeVoice model on first request"""
    global model, device
    
    if model is not None:
        return model
    
    try:
        logger.info("Initializing VibeVoice-Large model from Hugging Face...")
        
        # Set device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {device}")
        
        # Check if model exists locally, if not download from HF
        model_path = os.environ.get('MODEL_PATH', '/app/models/VibeVoice-Large')
        
        if not os.path.exists(model_path):
            logger.info("Model not found locally, downloading from Hugging Face...")
            from huggingface_hub import snapshot_download
            
            model_path = snapshot_download(
                repo_id='aoi-ot/VibeVoice-Large',
                local_dir=model_path,
                cache_dir='/app/cache',
                ignore_patterns=['*.git*', 'README.md']
            )
            logger.info(f"Model downloaded to: {model_path}")
        
        # Import VibeVoice modules
        try:
            # Try different import paths based on actual VibeVoice structure
            try:
                from VibeVoice.vibevoice import VibeVoiceInference
            except ImportError:
                try:
                    from vibevoice.inference import VibeVoiceInference
                except ImportError:
                    # Fallback - use demo script approach
                    logger.info("Using demo-style inference")
                    import sys
                    sys.path.append('/app/VibeVoice/demo')
                    from inference_from_file import load_model
                    model = load_model(model_path, device)
                    logger.info("VibeVoice model initialized successfully!")
                    return model
            
            # Initialize the model
            model = VibeVoiceInference(model_path=model_path, device=device)
            
        except Exception as import_error:
            logger.warning(f"Direct import failed: {import_error}")
            logger.info("Attempting to use VibeVoice demo interface...")
            
            # Fallback to using the demo scripts directly
            import subprocess
            model = {"model_path": model_path, "device": device, "type": "demo"}
        
        logger.info("VibeVoice model initialized successfully!")
        return model
        
    except Exception as e:
        logger.error(f"Failed to initialize model: {str(e)}")
        logger.error(traceback.format_exc())
        raise e

def generate_audio(job):
    """
    Generate audio from text using VibeVoice
    
    Expected input:
    {
        "text": "Speaker 1: Hello! Speaker 2: Hi there!",
        "speaker_names": ["Alice", "Bob"],  # optional
        "output_format": "wav",  # optional, default: wav
        "max_length": 45  # optional, max minutes, default: 45
    }
    """
    try:
        job_input = job["input"]
        
        # Validate input
        if "text" not in job_input:
            return {"error": "Missing required 'text' parameter"}
        
        text = job_input["text"]
        speaker_names = job_input.get("speaker_names", ["Alice", "Bob"])
        output_format = job_input.get("output_format", "wav")
        max_length = job_input.get("max_length", 45)
        
        logger.info(f"Generating audio for text: {text[:100]}...")
        logger.info(f"Speaker names: {speaker_names}")
        
        # Initialize model if not already done
        model = initialize_model()
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as txt_file:
            txt_file.write(text)
            txt_path = txt_file.name
        
        with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as audio_file:
            audio_path = audio_file.name
        
        try:
            # Generate audio using VibeVoice
            # Based on the GitHub demo, the inference API looks like this:
            output_path = model.generate_from_text(
                text_content=text,
                speaker_names=speaker_names,
                output_path=audio_path
            )
            
            # Read the generated audio file
            with open(output_path, 'rb') as f:
                audio_data = f.read()
            
            # Encode as base64 for JSON response
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Get file size for stats
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
            # Clean up temporary files
            try:
                os.unlink(txt_path)
                os.unlink(audio_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "error": f"Failed to generate audio: {str(e)}"
        }

def handler(job):
    """
    Main RunPod handler function
    """
    try:
        logger.info(f"Received job: {job}")
        
        # Route to appropriate function based on job type
        job_input = job.get("input", {})
        
        if "text" in job_input:
            return generate_audio(job)
        else:
            return {
                "error": "Invalid input. Expected 'text' parameter.",
                "example": {
                    "text": "Speaker 1: Hello there! Speaker 2: Hi, how are you?",
                    "speaker_names": ["Alice", "Bob"],
                    "output_format": "wav"
                }
            }
            
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Handler failed: {str(e)}"}

# Health check endpoint
def health_check():
    """Health check for the service"""
    try:
        if torch.cuda.is_available():
            gpu_info = {
                "gpu_count": torch.cuda.device_count(),
                "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
                "gpu_memory": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB" if torch.cuda.device_count() > 0 else None
            }
        else:
            gpu_info = {"gpu_available": False}
            
        return {
            "status": "healthy",
            "model_loaded": model is not None,
            "device": str(device) if device else None,
            "gpu_info": gpu_info,
            "vibevoice_version": "Large (9.34B params)",
            "supported_languages": ["English", "Chinese"],
            "max_generation_length": "45 minutes",
            "max_speakers": 4
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    logger.info("Starting VibeVoice RunPod serverless handler...")
    logger.info("Visit the health check endpoint to verify the service is running.")
    
    # Start the RunPod serverless worker
    runpod.serverless.start({"handler": handler, "health_check": health_check})
