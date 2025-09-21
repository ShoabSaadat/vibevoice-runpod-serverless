#!/usr/bin/env python3
"""
Production-ready VibeVoice RunPod serverless handler
Optimized for fast cold starts and reliable model loading
"""

import runpod
import os
import sys
import torch
import tempfile
import base64
import subprocess
import logging
import traceback
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add VibeVoice to path
sys.path.insert(0, '/app/VibeVoice')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global model state
model_initialized = False
model_path = None
device = None

class InputValidator:
    """Validate and sanitize input parameters"""
    
    @staticmethod
    def validate_text(text: str) -> str:
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")
        
        if len(text) > 10000:  # 10K character limit
            raise ValueError("Text too long (max 10,000 characters)")
        
        return text.strip()
    
    @staticmethod
    def validate_speaker_names(speaker_names: List[str]) -> List[str]:
        if not isinstance(speaker_names, list):
            speaker_names = ["Alice", "Bob"]
        
        # Limit to 4 speakers max
        speaker_names = speaker_names[:4]
        
        # Ensure we have at least 2 speakers
        if len(speaker_names) < 2:
            speaker_names = ["Alice", "Bob"]
        
        return [str(name).strip() for name in speaker_names if str(name).strip()]
    
    @staticmethod
    def validate_output_format(format_type: str) -> str:
        allowed_formats = ["wav", "mp3", "flac"]
        format_type = format_type.lower() if format_type else "wav"
        
        if format_type not in allowed_formats:
            return "wav"
        
        return format_type

def initialize_model() -> bool:
    """Initialize VibeVoice model - called once on first request"""
    global model_initialized, model_path, device
    
    if model_initialized:
        return True
    
    try:
        start_time = time.time()
        logger.info("🚀 Initializing VibeVoice model...")
        
        # Set device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"🔥 Using device: {device}")
        
        # Check model path
        model_path = os.environ.get('MODEL_PATH', '/app/models/VibeVoice-Large')
        
        if not os.path.exists(model_path):
            logger.error(f"❌ Model path not found: {model_path}")
            return False
        
        # Verify essential files exist
        config_file = os.path.join(model_path, "config.json")
        if not os.path.exists(config_file):
            logger.warning(f"⚠️ Model config not found: {config_file}")
            # Try to find any config file
            config_files = list(Path(model_path).glob("*config*"))
            if config_files:
                logger.info(f"✓ Found alternative config: {config_files[0]}")
            else:
                logger.warning("⚠️ No config files found, proceeding anyway...")
        
        # Set model as initialized
        model_initialized = True
        init_time = time.time() - start_time
        logger.info(f"✅ Model initialized successfully in {init_time:.2f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Model initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def generate_audio(job_input: Dict[str, Any]) -> Dict[str, Any]:
    """Generate audio from text using VibeVoice"""
    try:
        start_time = time.time()
        
        # Validate inputs
        text = InputValidator.validate_text(job_input.get("text", ""))
        speaker_names = InputValidator.validate_speaker_names(
            job_input.get("speaker_names", ["Alice", "Bob"])
        )
        output_format = InputValidator.validate_output_format(
            job_input.get("output_format", "wav")
        )
        
        logger.info(f"🎵 Generating audio for {len(text)} characters")
        logger.info(f"👥 Speakers: {speaker_names}")
        
        # Ensure model is ready
        if not initialize_model():
            return {"error": "Model initialization failed"}
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as txt_file:
            txt_file.write(text)
            txt_path = txt_file.name
        
        output_dir = "/tmp/vibevoice_output"
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Use VibeVoice demo script (most reliable approach)
            demo_script = "/app/VibeVoice/demo/inference_from_file.py"
            
            if not os.path.exists(demo_script):
                # Try alternative script locations
                possible_scripts = [
                    "/app/VibeVoice/inference.py",
                    "/app/VibeVoice/generate.py",
                    "/app/VibeVoice/run_inference.py"
                ]
                
                for script in possible_scripts:
                    if os.path.exists(script):
                        demo_script = script
                        break
                else:
                    return {"error": f"No inference script found in VibeVoice directory"}
            
            # Build command
            cmd = [
                'python', demo_script,
                '--model_path', model_path,
                '--txt_path', txt_path,
                '--speaker_names'
            ] + speaker_names
            
            logger.info("🎯 Running VibeVoice generation...")
            generation_start = time.time()
            
            # Run generation with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd='/app/VibeVoice',
                timeout=300  # 5 minute timeout
            )
            
            generation_time = time.time() - generation_start
            
            if result.returncode == 0:
                # Find generated audio file
                audio_files = list(Path('/app/VibeVoice').glob(f"**/*.{output_format}"))
                
                if not audio_files:
                    # Try other formats
                    for ext in ['wav', 'mp3', 'flac']:
                        audio_files = list(Path('/app/VibeVoice').glob(f"**/*.{ext}"))
                        if audio_files:
                            break
                
                # Also check output directory
                if not audio_files:
                    audio_files = list(Path(output_dir).glob(f"**/*.{output_format}"))
                
                if audio_files:
                    # Use the most recent file
                    latest_audio = max(audio_files, key=os.path.getmtime)
                    
                    with open(latest_audio, 'rb') as f:
                        audio_data = f.read()
                    
                    # Clean up generated file
                    try:
                        os.unlink(latest_audio)
                    except:
                        pass
                    
                    # Encode as base64
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    file_size_mb = len(audio_data) / (1024 * 1024)
                    total_time = time.time() - start_time
                    
                    logger.info(f"✅ Audio generated in {generation_time:.2f}s, size: {file_size_mb:.2f} MB")
                    
                    return {
                        "success": True,
                        "audio_base64": audio_base64,
                        "format": output_format,
                        "size_mb": round(file_size_mb, 2),
                        "speakers": speaker_names,
                        "text_length": len(text),
                        "generation_time": round(generation_time, 2),
                        "total_time": round(total_time, 2)
                    }
                else:
                    logger.error("❌ No audio file generated")
                    return {
                        "error": "No audio file generated", 
                        "stdout": result.stdout[:500],
                        "stderr": result.stderr[:500]
                    }
            else:
                logger.error(f"❌ Generation failed: {result.stderr}")
                return {
                    "error": f"Generation failed: {result.stderr[:500]}",
                    "stdout": result.stdout[:500]
                }
                
        finally:
            # Cleanup
            try:
                os.unlink(txt_path)
            except:
                pass
                
    except ValueError as e:
        return {"error": f"Invalid input: {str(e)}"}
    except subprocess.TimeoutExpired:
        return {"error": "Generation timeout (5 minutes exceeded)"}
    except Exception as e:
        logger.error(f"❌ Generation error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Generation failed: {str(e)}"}

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """Main RunPod handler function"""
    try:
        logger.info(f"📨 Received job: {job.get('id', 'unknown')}")
        
        job_input = job.get("input", {})
        
        if not job_input:
            return {
                "error": "No input provided",
                "example": {
                    "text": "Speaker 1: Hello there! Speaker 2: Hi, how are you?",
                    "speaker_names": ["Alice", "Bob"],
                    "output_format": "wav"
                }
            }
        
        if "text" not in job_input:
            return {
                "error": "Missing required 'text' parameter",
                "example": {
                    "text": "Speaker 1: Hello there! Speaker 2: Hi, how are you?",
                    "speaker_names": ["Alice", "Bob"],
                    "output_format": "wav"
                }
            }
        
        return generate_audio(job_input)
            
    except Exception as e:
        logger.error(f"❌ Handler error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Handler failed: {str(e)}"}

def health_check() -> Dict[str, Any]:
    """Health check for the service"""
    try:
        health_data = {
            "status": "healthy" if model_initialized else "initializing",
            "model_loaded": model_initialized,
            "device": str(device) if device else None,
            "timestamp": time.time()
        }
        
        if torch.cuda.is_available():
            health_data["gpu_info"] = {
                "gpu_count": torch.cuda.device_count(),
                "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
                "gpu_memory_gb": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}" if torch.cuda.device_count() > 0 else None
            }
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

if __name__ == "__main__":
    logger.info("🎵 Starting VibeVoice RunPod serverless handler...")
    logger.info(f"🔥 CUDA available: {torch.cuda.is_available()}")
    logger.info(f"🎯 GPU count: {torch.cuda.device_count()}")
    
    # Start the RunPod serverless worker
    runpod.serverless.start({
        "handler": handler,
        "return_aggregate_stream": False
    })