#!/usr/bin/env python3
"""
Simple Bitquery API connectivity test
Place this file in your project root directory
"""
import asyncio
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.bitquery_api import call_bitquery_api
from config import BITQUERY_API_KEY, BITQUERY_API_URL

async def test_basic_connection():
    """Test basic Bitquery API connectivity"""
    print("🧪 Testing Bitquery API Connection...")
    print(f"📍 API URL: {BITQUERY_API_URL}")
    print(f"🔑 API Key Present: {bool(BITQUERY_API_KEY)}")
    print(f"🔑 API Key Length: {len(BITQUERY_API_KEY) if BITQUERY_API_KEY else 0}")
    
    # Simple test query
    test_query = """
    {
      Solana {
        DEXTrades(limit: {count: 1}) {
          Transaction {
            Signature
          }
          Block {
            Time
          }
        }
      }
    }
    """
    
    try:
        result = await call_bitquery_api(test_query)
        
        if result is None:
            print("❌ API returned None")
            return False
            
        if "errors" in result:
            print(f"❌ GraphQL Errors: {result['errors']}")
            return False
            
        if "data" in result and result["data"]:
            print("✅ API Connection Successful!")
            print(f"📊 Sample Data: {result}")
            return True
        else:
            print("❌ No data in response")
            print(f"🔍 Full Response: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_basic_connection())