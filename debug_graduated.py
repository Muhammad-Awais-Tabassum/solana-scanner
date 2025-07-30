#!/usr/bin/env python3
"""
Debug graduated token detection
Place this file in your project root directory
"""
import asyncio
import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from filters.graduated_checks import debug_graduated_check

async def main():
    print("🚀 Starting Graduated Token Debug Test...")
    print("=" * 50)
    
    try:
        tokens = await debug_graduated_check()
        print(f"\n🎯 Final Result: Found {len(tokens)} graduated tokens")
        
        if tokens:
            print("📋 Token Details:")
            for i, token in enumerate(tokens, 1):
                print(f"  {i}. {token}")
        else:
            print("⚠️  No tokens found - check the debug output above")
            
    except Exception as e:
        print(f"❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())