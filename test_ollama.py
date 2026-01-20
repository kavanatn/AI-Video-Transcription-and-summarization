import requests
import json

def test_ollama():
    print("Testing Ollama Connection...")
    url = "http://localhost:11434/api/generate"
    model = "llama3.2"
    
    payload = {
        "model": model,
        "prompt": "Say 'Ollama is working!' if you can hear me.",
        "stream": False
    }
    
    try:
        print(f"Sending request to {url} with model {model}...")
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            res_json = response.json()
            print("Response:", res_json.get("response"))
            print("SUCCESS: Ollama is reachable and responding.")
        else:
            print(f"FAILED: Status Code {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("FAILED: Could not connect to localhost:11434. Is 'ollama serve' running?")
    except Exception as e:
        print(f"FAILED: Unexpected error: {e}")

if __name__ == "__main__":
    test_ollama()
