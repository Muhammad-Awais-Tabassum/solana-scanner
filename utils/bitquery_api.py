# bitquery_api.py

import requests
from config import BITQUERY_API_KEY

def call_bitquery_api(query, variables=None):
    url = "https://streaming.bitquery.io/graphql"

    headers = {
        'Authorization': 'Bearer ory_at_rXPN_9zkuWmM6l0s0nXN-0bElrNmkk132aI9y76VdTE.9atktM_b4Vu2oh25vi_RUK0ttEk-h2_GjJ7YipeRqYA',
        'Content-Type': 'application/json'
    }

    payload = {
        "query": query,
        "variables": variables or {}
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # raises error for 4xx/5xx

        data = response.json()

        # 🔍 Debugging: check if 'data' is missing
        if not data or "data" not in data:
            print("[ERROR] Bitquery response missing 'data' field.")
            print("[DEBUG] Full Bitquery response:", data)
            return None

        return data

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Exception during Bitquery request: {e}")
        print("[DEBUG] Request payload:", payload)
        return None

    except ValueError as e:
        print(f"[ERROR] Failed to decode Bitquery JSON response: {e}")
        print("[DEBUG] Raw response text:", response.text)
        return None
