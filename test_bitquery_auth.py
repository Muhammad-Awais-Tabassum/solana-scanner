# test_bitquery_auth.py
import asyncio
import aiohttp
import json
from config import BITQUERY_API_KEY, BITQUERY_API_URL

async def test_bitquery_auth():
    """Test different authentication methods with Bitquery"""
    
    if not BITQUERY_API_KEY:
        print("❌ No API key found!")
        return
    
    print(f"🔑 Testing API Key: {BITQUERY_API_KEY[:10]}...{BITQUERY_API_KEY[-10:]}")
    print(f"📍 API URL: {BITQUERY_API_URL}")
    
    # Simple test query
    test_query = """
    {
      Solana {
        DEXTrades(limit: {count: 1}) {
          Transaction {
            Signature
          }
        }
      }
    }
    """
    
    # Test different header formats
    auth_methods = [
        {
            'name': 'X-API-KEY Header',
            'headers': {
                'Content-Type': 'application/json',
                'X-API-KEY': BITQUERY_API_KEY
            }
        },
        {
            'name': 'Authorization Bearer Header', 
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {BITQUERY_API_KEY}'
            }
        },
        {
            'name': 'Authorization Header (no Bearer)',
            'headers': {
                'Content-Type': 'application/json', 
                'Authorization': BITQUERY_API_KEY
            }
        }
    ]
    
    for method in auth_methods:
        print(f"\n🧪 Testing {method['name']}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    BITQUERY_API_URL,
                    headers=method['headers'],
                    json={'query': test_query},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    status = response.status
                    text = await response.text()
                    
                    print(f"   Status: {status}")
                    print(f"   Response: {text[:200]}...")
                    
                    if status == 200:
                        print(f"   ✅ {method['name']} WORKS!")
                        return method['headers']
                    elif status == 401:
                        print(f"   ❌ {method['name']} - Unauthorized")
                    else:
                        print(f"   ⚠️  {method['name']} - Status {status}")
                        
        except Exception as e:
            print(f"   ❌ {method['name']} - Error: {e}")
    
    print("\n❌ All authentication methods failed!")
    print("🔍 Please check your API key at: https://account.bitquery.io/")
    return None

if __name__ == "__main__":
    asyncio.run(test_bitquery_auth())