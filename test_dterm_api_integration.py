
import requests
import json
import time

BASE_URL = "http://localhost:5000"
PROJECT_ID = "D조건_251001~251231_20260105_110824" # User provided project name

def test_extraction():
    url = f"{BASE_URL}/api/projects/{PROJECT_ID}/step3/dterm/extract"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.post(url, json={"target_ids": None}) # Process all
        
        if response.status_code == 200:
            print("✅ Success! Response:")
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Failed with Status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_extraction()
