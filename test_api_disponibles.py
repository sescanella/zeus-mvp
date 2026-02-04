"""Test API endpoint for disponibles unions."""
import sys
import requests
import json

# Test the disponibles endpoint
url = "http://localhost:8000/api/v4/uniones/TEST-02/disponibles"
params = {"operacion": "ARM"}

try:
    response = requests.get(url, params=params, timeout=5)

    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nResponse Body:")

    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        print(f"\n✅ SUCCESS: Found {data.get('count', 0)} disponibles unions")
    else:
        print(f"❌ ERROR: {response.text}")
        sys.exit(1)

except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to backend. Is it running on port 8000?")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
