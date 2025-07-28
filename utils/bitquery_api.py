#utils/bitquery_api.py

import aiohttp
import asyncio
from config import BITQUERY_API_KEY

async def call_bitquery_api(query, variables=None):
    url = "https://streaming.bitquery.io/graphql"

    headers = {
        'Authorization': f'Bearer {BITQUERY_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "query": query,
        "variables": variables or {}
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"[ERROR] Bitquery API returned status {response.status}")
                    print(text)
                    return None
    except Exception as e:
        print(f"[ERROR] Bitquery API call failed: {e}")
        return None
