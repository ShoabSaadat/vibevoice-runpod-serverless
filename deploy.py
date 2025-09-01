#!/usr/bin/env python3

import requests
import json
import os
import time

# Configuration
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
GITHUB_REPO_URL = "https://github.com/YOUR-USERNAME/vibevoice-runpod-serverless"  # Update this!

def create_serverless_endpoint():
    """Create a serverless endpoint using RunPod API"""
    
    if not RUNPOD_API_KEY:
        print("❌ Please set RUNPOD_API_KEY environment variable")
        return False
    
    url = "https://api.runpod.ai/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    # GraphQL mutation to create endpoint
    mutation = """
    mutation {
        saveTemplate(input: {
            containerDiskInGb: 50
            dockerArgs: ""
            env: [
                {key: "MODEL_PATH", value: "/app/models/VibeVoice-Large"}
                {key: "TRANSFORMERS_CACHE", value: "/app/cache"}
                {key: "HF_HOME", value: "/app/cache"}
                {key: "PYTORCH_CUDA_ALLOC_CONF", value: "max_split_size_mb:512"}
            ]
            imageName: "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04"
            isPublic: false
            isServerless: true
            name: "VibeVoice-Large-Serverless"
            ports: "8000/http"
            readme: "VibeVoice-Large serverless deployment"
            volumeInGb: 0
            volumeMountPath: ""
        }) {
            id
            name
        }
    }
    """
    
    try:
        response = requests.post(url, headers=headers, json={"query": mutation})
        
        if response.status_code == 200:
            result = response.json()
            
            if "errors" in result:
                print(f"❌ GraphQL errors: {result['errors']}")
                return False
                
            template_id = result["data"]["saveTemplate"]["id"]
            print(f"✅ Template created with ID: {template_id}")
            
            # Now create the endpoint
            endpoint_mutation = f"""
            mutation {{
                createEndpoint(input: {{
                    templateId: "{template_id}"
                    name: "vibevoice-large-endpoint"
                    workersMax: 1
                    workersMin: 0
                    idleTimeout: 5
                    scalerType: "QUEUE_DELAY"
                    scalerValue: 1
                    gpuIds: "NVIDIA GeForce RTX 4090,NVIDIA RTX A6000,NVIDIA A100 80GB PCIe"
                }}) {{
                    id
                    name
                }}
            }}
            """
            
            endpoint_response = requests.post(url, headers=headers, json={"query": endpoint_mutation})
            
            if endpoint_response.status_code == 200:
                endpoint_result = endpoint_response.json()
                
                if "errors" in endpoint_result:
                    print(f"❌ Endpoint creation errors: {endpoint_result['errors']}")
                    return False
                
                endpoint_id = endpoint_result["data"]["createEndpoint"]["id"]
                print(f"✅ Endpoint created with ID: {endpoint_id}")
                print(f"🔗 Endpoint URL: https://api.runpod.ai/v2/{endpoint_id}")
                return endpoint_id
            else:
                print(f"❌ Failed to create endpoint: {endpoint_response.status_code}")
                return False
        else:
            print(f"❌ Failed to create template: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 VibeVoice-Large Serverless Deployment")
    print("=" * 50)
    
    print("\n📋 Pre-deployment checklist:")
    print("1. ✅ Files created locally")
    print("2. ✅ Git repository initialized")
    print("3. 🔄 Push to GitHub...")
    
    # Instructions for GitHub push
    print(f"\n📤 Push your code to GitHub:")
    print(f"   git remote add origin {GITHUB_REPO_URL}")
    print(f"   git branch -M main")
    print(f"   git push -u origin main")
    print(f"\n   Or create a new repo at: https://github.com/new")
    
    print(f"\n🔧 Alternative deployment methods:")
    
    print(f"\n📝 Method 1: RunPod Web Interface (Recommended)")
    print(f"   1. Go to: https://runpod.io/serverless")
    print(f"   2. Click 'New Endpoint'")
    print(f"   3. Select 'Source Code' tab")
    print(f"   4. Enter GitHub URL: {GITHUB_REPO_URL}")
    print(f"   5. Set handler: handler.py")
    print(f"   6. Choose GPU: RTX 4090, A6000, or A100")
    print(f"   7. Deploy!")
    
    print(f"\n🐳 Method 2: Docker Hub")
    print(f"   1. Build: docker build -t your-username/vibevoice-large .")
    print(f"   2. Push: docker push your-username/vibevoice-large")
    print(f"   3. Use Docker image in RunPod serverless")
    
    print(f"\n⚡ Method 3: API Deployment (Experimental)")
    create_endpoint = input(f"   Try API deployment? (y/n): ").lower().strip()
    
    if create_endpoint == 'y':
        endpoint_id = create_serverless_endpoint()
        if endpoint_id:
            print(f"\n🎉 Deployment successful!")
            print(f"   Endpoint ID: {endpoint_id}")
            print(f"   Test with: python test_endpoint.py")
    
    print(f"\n✨ Deployment options ready!")
    print(f"   Choose the method that works best for you.")

if __name__ == "__main__":
    main()
