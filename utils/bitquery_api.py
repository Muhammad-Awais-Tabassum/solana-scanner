# bitquery_api.py

import requests
from config import BITQUERY_API_KEY

def call_bitquery_api(query, variables=None):
    url = "https://streaming.bitquery.io/graphql"

    headers = {
        'Authorization': f'Bearer {BITQUERY_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "query": query,
        "variables": variables or {}
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"[ERROR] Bitquery API returned status {response.status_code}")
        print(response.text)
        return None