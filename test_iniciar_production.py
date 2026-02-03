#!/usr/bin/env python3
"""
Test script to reproduce the v4.0 INICIAR error from production.
"""
import requests
import json

# Production URL
BASE_URL = "https://zeues-backend-mvp-production.up.railway.app"

# Test data - modify with a real v4.0 spool from your sheets
payload = {
    "tag_spool": "TEST-01",  # Replace with a real v4.0 spool TAG
    "worker_id": 93,
    "worker_nombre": "MR(93)",
    "operacion": "ARM"
}

print(f"Testing INICIAR endpoint at {BASE_URL}/api/v4/occupation/iniciar")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("-" * 60)

try:
    response = requests.post(
        f"{BASE_URL}/api/v4/occupation/iniciar",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("-" * 60)

    if response.status_code == 500:
        print("ERROR 500 - Internal Server Error")
        print(f"Response Text: {response.text}")

        try:
            error_detail = response.json()
            print(f"\nParsed JSON Error:")
            print(json.dumps(error_detail, indent=2))
        except:
            print("Could not parse response as JSON")
    else:
        print(f"Response Body:")
        print(json.dumps(response.json(), indent=2))

except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
