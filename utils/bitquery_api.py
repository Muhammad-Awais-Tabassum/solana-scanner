# utils/bitquery_api.py - Enhanced Debug Version
import aiohttp
import asyncio
import json
from config import BITQUERY_API_URL, BITQUERY_API_KEY

async def call_bitquery_api(query, variables=None):
    """
    Async function to call Bitquery GraphQL API with enhanced debugging
    """
    print(f"[DEBUG] Bitquery API URL: {BITQUERY_API_URL}")
    print(f"[DEBUG] API Key present: {bool(BITQUERY_API_KEY)}")
    print(f"[DEBUG] API Key length: {len(BITQUERY_API_KEY) if BITQUERY_API_KEY else 0}")
    
    headers = {
    'Content-Type': 'application/json', 
    'Authorization': f'Bearer {BITQUERY_API_KEY}'
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    # Log the query being sent (truncated for readability)
    query_preview = query[:200] + "..." if len(query) > 200 else query
    print(f"[DEBUG] Query preview: {query_preview}")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            print("[DEBUG] Making API request...")
            
            async with session.post(BITQUERY_API_URL, json=payload, headers=headers) as response:
                print(f"[DEBUG] Response status: {response.status}")
                print(f"[DEBUG] Response headers: {dict(response.headers)}")
                
                response_text = await response.text()
                print(f"[DEBUG] Response text (first 500 chars): {response_text[:500]}")
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        print(f"[DEBUG] Successfully parsed JSON response")
                        print(f"[DEBUG] Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                        
                        # Check for GraphQL errors
                        if "errors" in result:
                            print(f"[ERROR] GraphQL errors: {result['errors']}")
                            return None
                            
                        return result
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] Failed to parse JSON: {e}")
                        return None
                else:
                    print(f"[ERROR] Bitquery API error: {response.status}")
                    print(f"[ERROR] Response body: {response_text}")
                    return None
                    
    except asyncio.TimeoutError:
        print("[ERROR] Bitquery API timeout (60s)")
        return None
    except aiohttp.ClientError as e:
        print(f"[ERROR] HTTP client error: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Bitquery API call failed: {e}")
        import traceback
        traceback.print_exc()
        return None
