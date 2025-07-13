# bitquery_api.py
import json
import traceback
import requests
from config import BITQUERY_API_KEY

def call_bitquery_api(query, variables=None):
    url = "https://graphql.bitquery.io/"
    
    headers = {
        'Authorization': f'Bearer {BITQUERY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "query": query,
        "variables": variables or {}
    }
    
    try:
        print(f"🔍 Making API call to: {url}")
        print(f"📝 Query variables: {json.dumps(variables, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"📡 Response status: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")
        
        if response.status_code >= 400:
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return None
        
        # Try to parse JSON
        try:
            data = response.json()
            print(f"✅ JSON Response received: {json.dumps(data, indent=2)[:1000]}...")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            print(f"Raw response: {response.text}")
            return None
        
        # Check for GraphQL errors
        if "errors" in data:
            print(f"[ERROR] GraphQL errors: {json.dumps(data['errors'], indent=2)}")
            return None
        
        # Check data structure
        if not data.get('data'):
            print(f"[ERROR] No 'data' field in response: {data}")
            return None
            
        return data
        
    except Exception as e:
        print(f"[ERROR] Exception during API call: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return None
