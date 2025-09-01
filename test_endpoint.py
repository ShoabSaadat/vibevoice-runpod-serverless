#!/usr/bin/env python3

import requests
import json
import base64
import time
import os

# Configuration - UPDATE THESE!
ENDPOINT_URL = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID"  # Replace with your endpoint
API_KEY = os.getenv("RUNPOD_API_KEY", "YOUR_API_KEY")  # Set via environment or replace

def test_health_check():
    """Test if the endpoint is healthy"""
    print("🔍 Testing health check...")
    
    try:
        response = requests.get(f"{ENDPOINT_URL}/health", timeout=30)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_audio_generation(test_case="basic"):
    """Test audio generation with different inputs"""
    
    test_cases = {
        "basic": {
            "text": "Speaker 1: Hello! Welcome to VibeVoice. Speaker 2: This is incredible quality!",
            "speaker_names": ["Alice", "Bob"],
            "description": "Basic 2-speaker conversation"
        },
        "podcast": {
            "text": "Host: Welcome to Tech Talk Today! Our guest is an AI researcher. Guest: Thanks for having me. I'm excited to discuss the future of voice synthesis. Host: Let's start with VibeVoice - what makes it special?",
            "speaker_names": ["Host", "Expert"],
            "description": "Podcast-style dialogue"
        },
        "multilingual": {
            "text": "Speaker 1: Hello, how are you today? Speaker 2: 你好！我很好，谢谢。Today is a beautiful day.",
            "speaker_names": ["Emma", "Li"],
            "description": "Mixed English-Chinese conversation"
        }
    }
    
    test_data = test_cases.get(test_case, test_cases["basic"])
    
    print(f"🎙️ Testing audio generation: {test_data['description']}")
    print(f"Text: {test_data['text'][:100]}...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "input": {
            "text": test_data["text"],
            "speaker_names": test_data["speaker_names"],
            "output_format": "wav"
        }
    }
    
    try:
        print("⏳ Sending request...")
        start_time = time.time()
        
        # Use runsync for synchronous execution
        response = requests.post(f"{ENDPOINT_URL}/runsync", json=payload, headers=headers, timeout=300)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️ Request completed in {duration:.1f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Response status: {response.status_code}")
            print(f"Response keys: {list(result.keys())}")
            
            if "output" in result and result["output"].get("success"):
                output = result["output"]
                print(f"✅ Audio generation successful!")
                print(f"   Size: {output.get('size_mb', 'unknown')} MB")
                print(f"   Format: {output.get('format', 'unknown')}")
                print(f"   Speakers: {output.get('speakers', [])}")
                print(f"   Text length: {output.get('text_length', 0)} characters")
                
                # Save the audio file
                if "audio_base64" in output:
                    audio_data = base64.b64decode(output["audio_base64"])
                    filename = f"test_output_{test_case}_{int(time.time())}.wav"
                    
                    with open(filename, "wb") as f:
                        f.write(audio_data)
                    
                    print(f"💾 Audio saved as: {filename}")
                    return True
                else:
                    print("❌ No audio data in response")
                    return False
            else:
                error_msg = result.get("output", {}).get("error", "Unknown error")
                print(f"❌ Generation failed: {error_msg}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>300 seconds)")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 VibeVoice-Large Serverless Endpoint Tester")
    print("=" * 50)
    
    if not API_KEY or API_KEY == "YOUR_API_KEY":
        print("❌ Please set your RunPod API key!")
        print("   export RUNPOD_API_KEY='your-key-here'")
        return
    
    if "YOUR_ENDPOINT_ID" in ENDPOINT_URL:
        print("❌ Please update ENDPOINT_URL with your actual endpoint!")
        return
    
    # Test 1: Health Check
    print("\n1️⃣ Health Check Test")
    health_ok = test_health_check()
    
    if not health_ok:
        print("❌ Skipping audio tests due to health check failure")
        return
    
    # Test 2: Basic Audio Generation
    print("\n2️⃣ Basic Audio Generation Test")
    basic_ok = test_audio_generation("basic")
    
    # Test 3: Podcast Style (if basic worked)
    if basic_ok:
        print("\n3️⃣ Podcast Style Test")
        test_audio_generation("podcast")
        
        print("\n4️⃣ Multilingual Test")
        test_audio_generation("multilingual")
    
    print("\n🎉 Testing complete!")
    print("\nTo use your endpoint:")
    print(f"   Endpoint URL: {ENDPOINT_URL}/runsync")
    print(f"   API Key: {API_KEY[:8]}...")

if __name__ == "__main__":
    main()
