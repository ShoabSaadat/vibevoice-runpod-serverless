# VibeVoice-Large Serverless Deployment

This is a RunPod serverless deployment of Microsoft's **VibeVoice-Large** model (9.34B parameters) for high-quality text-to-speech generation.

## Model Features
- **Size**: 9.34B parameters
- **Context Length**: 32K tokens (~45 minutes generation)
- **Languages**: English, Chinese
- **Speakers**: Up to 4 distinct speakers
- **Quality**: Frontier-level conversational TTS with natural turn-taking

## Deployment Options

### Option 1: Use Pre-built Files (Recommended)

1. Upload these files to RunPod Serverless:
   - `handler.py`
   - `Dockerfile`
   - `requirements.txt`

2. Configure in RunPod dashboard:
   - **Base Image**: `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04`
   - **Handler**: `handler.py`
   - **GPU**: RTX 4090, RTX A6000, or A100 (30GB+ VRAM)
   - **Container Disk**: 50GB+
   - **Timeout**: 300s+

### Option 2: Manual Build

1. Build the Docker image:
```bash
docker build -t vibevoice-large-serverless .
```

2. Push to your container registry
3. Deploy via RunPod serverless

## API Usage

Once deployed, use the endpoint like this:

```python
import requests
import json
import base64

# Your RunPod endpoint URL
endpoint_url = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
api_key = "YOUR_API_KEY"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "input": {
        "text": "Speaker 1: Hello! Welcome to VibeVoice. Speaker 2: This is amazing quality!",
        "speaker_names": ["Alice", "Bob"],
        "output_format": "wav"
    }
}

response = requests.post(endpoint_url, json=payload, headers=headers)
result = response.json()

# Save the audio file
if result.get("output", {}).get("success"):
    audio_data = base64.b64decode(result["output"]["audio_base64"])
    with open("generated_audio.wav", "wb") as f:
        f.write(audio_data)
    print(f"Audio saved! Size: {result['output']['size_mb']} MB")
```

## Input Parameters

- **text** (required): The dialogue text with speaker labels
- **speaker_names** (optional): List of speaker names (default: ["Alice", "Bob"])
- **output_format** (optional): Audio format (default: "wav")
- **max_length** (optional): Maximum generation length in minutes (default: 45)

## Example Inputs

### Basic Conversation
```json
{
    "text": "Speaker 1: Good morning! How are you today? Speaker 2: I'm doing great, thank you for asking!",
    "speaker_names": ["Sarah", "Mike"]
}
```

### Podcast Style
```json
{
    "text": "Host: Welcome to our show! Today we're discussing AI. Guest: Thanks for having me. This technology is fascinating.",
    "speaker_names": ["Host", "Expert"]
}
```

## Cost Estimation

**Serverless Pricing (Pay-per-use)**:
- ~$0.0002-0.0005 per second of inference
- Average 30-60 seconds for 1-2 minute audio
- **Cost per minute of audio**: ~$0.006-0.03

**Comparison**:
- Much cheaper than Replicate ($0.0135/min)
- Only pay when generating audio
- Auto-scales to zero when idle

## Features

✅ **Pay-per-use**: Only charged during inference  
✅ **Auto-scaling**: Scales to zero when idle  
✅ **Fast cold start**: ~10-30 seconds  
✅ **High quality**: VibeVoice-Large model  
✅ **Multi-speaker**: Up to 4 speakers  
✅ **Long generation**: Up to 45 minutes  
✅ **RESTful API**: Easy integration  

## Limitations

- **Languages**: English and Chinese only
- **Content**: Speech-only (no music/background sounds)
- **GPU Requirements**: Needs 30GB+ VRAM
- **Research Use**: Intended for research/development

## Health Check

Check endpoint status:
```python
response = requests.get(f"{endpoint_url}/health")
print(response.json())
```

## Support

For issues with:
- **VibeVoice model**: https://github.com/microsoft/VibeVoice
- **RunPod platform**: RunPod support
- **This deployment**: Check handler.py logs in RunPod dashboard
