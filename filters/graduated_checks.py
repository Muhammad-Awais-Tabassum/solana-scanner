# filters/graduated_checks.py

import aiohttp
import asyncio 
from datetime import datetime, timedelta
from config import (
    GRADUATED_FILTERS,
    BIRDEYE_API_KEY,
    SHYFT_API_KEY,
)
from utils.bitquery_api import call_bitquery_api  # ✅ This is ASYNC!

BIRDEYE_TOKEN_INFO = "https://public-api.birdeye.so/public/token/"
SHYFT_METADATA_URL = "https://api.shyft.to/sol/v1/token/get_info?network=mainnet&token="

HEADERS_BIRDEYE = {"X-API-KEY": BIRDEYE_API_KEY}
HEADERS_SHYFT = {"x-api-key": SHYFT_API_KEY}

# ✅ FIXED - Updated graduation query (no GraphQL variables, direct string replacement)
GRADUATION_QUERY = """
{
  Solana {
    DEXPools(
      where: {
        Pool: {
          Dex: {
            ProtocolName: {is: "pump"}
          }
          Base: {
            PostAmount: {eq: "206900000"}
          }
        }
        Block: {
          Time: {
            since: "$time_start"
            till: "$time_end"
          }
        }
        Transaction: {Result: {Success: true}}
      }
      orderBy: {descending: Block_Time}
      limit: {count: 100}
    ) {
      Block {
        Time
      }
      Pool {
        Market {
          BaseCurrency {
            MintAddress
          }
        }
      }
    }
  }
}
"""

def get_time_range(minutes_back=60, min_seconds_ago=30):
    """Generate time range for querying graduated tokens"""
    now = datetime.utcnow()
    time_start = now - timedelta(minutes=minutes_back)
    time_end = now - timedelta(seconds=min_seconds_ago)
    return time_start.isoformat() + "Z", time_end.isoformat() + "Z"

def extract_mints_from_response(data):
    """Extract mint addresses from Bitquery response"""
    try:
        if not data or "data" not in data:
            print("[ERROR] Invalid Bitquery response structure")
            return []
            
        if "Solana" not in data["data"]:
            print("[ERROR] No Solana data in response")
            return []
            
        if "DEXPools" not in data["data"]["Solana"]:
            print("[ERROR] No DEXPools data in response")
            return []

        dex_pools = data["data"]["Solana"]["DEXPools"]
        mints = []
        
        for pool in dex_pools:
            try:
                mint = pool["Pool"]["Market"]["BaseCurrency"]["MintAddress"]
                if mint and mint != "":
                    mints.append(mint)
            except KeyError as e:
                print(f"[WARN] Missing field in pool data: {e}")
                continue
                
        # Remove duplicates
        unique_mints = list(set(mints))
        print(f"[INFO] Extracted {len(unique_mints)} unique mint addresses")
        return unique_mints
        
    except Exception as e:
        print(f"[ERROR] Failed to extract mints: {e}")
        return []
async def get_birdeye_data(session, mint):
    """Fetch token data from Birdeye API"""
    try:
        url = BIRDEYE_TOKEN_INFO + mint
        async with session.get(url, headers=HEADERS_BIRDEYE) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", {})
            elif resp.status == 429:
                print(f"[WARN] Birdeye rate limit for {mint}")
                await asyncio.sleep(1)  # Rate limit delay
                return {}
            else:
                print(f"[WARN] Birdeye API error {resp.status} for {mint}")
                return {}
    except Exception as e:
        print(f"[ERROR] Birdeye API failed for {mint}: {e}")
        return {}

async def get_token_metadata(session, mint):
    """Fetch token metadata from Shyft API"""
    try:
        url = SHYFT_METADATA_URL + mint
        async with session.get(url, headers=HEADERS_SHYFT) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get("result", {})
            elif resp.status == 429:
                print(f"[WARN] Shyft rate limit for {mint}")
                await asyncio.sleep(1)  # Rate limit delay
                return {}
            else:
                print(f"[WARN] Shyft API error {resp.status} for {mint}")
                return {}
    except Exception as e:
        print(f"[ERROR] Shyft API failed for {mint}: {e}")
        return {}

def apply_graduated_filters(birdeye_data, metadata):
    """Apply filters to graduated tokens"""
    try:
        # Extract Birdeye data
        market_cap = birdeye_data.get("mc", 0)
        volume_24h = birdeye_data.get("volume24h", 0)
        volume_1h = birdeye_data.get("volume1h", 0)
        price = birdeye_data.get("price_usd", 0)
        liquidity = birdeye_data.get("liquidity", 0)

        # Extract Shyft metadata
        token_info = metadata.get("token_info", {}) or {}
        dev_holdings = token_info.get("creator_token_holdings", 100)
        creators = metadata.get("creators", [])
        freeze_authority = token_info.get("freeze_authority", "")
        update_authority = token_info.get("update_authority", "")
        is_mutable = token_info.get("is_mutable", True)

        # Token distribution check
        top_holders = token_info.get("top_holders", [])
        holder_concentration = (
            sum(h.get("amount", 0) for h in top_holders[:5]) / token_info.get("supply", 1)
            if top_holders and token_info.get("supply") else 1.0
        )

        # 1. Market cap check
        if market_cap < GRADUATED_FILTERS["min_marketcap"]:
            return False, f"Market cap too low: ${market_cap:,.0f}"

        # 2. Volume check
        if volume_24h < GRADUATED_FILTERS["min_volume"]:
            return False, f"Volume too low: ${volume_24h:,.0f}"

        # 3. Volume stability (ensure some recent activity)
        if volume_1h and volume_1h < (0.05 * volume_24h):
            return False, f"Low recent trading activity (1h vol: ${volume_1h:,.0f})"

        # 4. Liquidity check
        if liquidity < GRADUATED_FILTERS.get("min_liquidity", 1000):
            return False, f"Liquidity too low: ${liquidity:,.0f}"

        # 5. Dev holding check
        if dev_holdings > GRADUATED_FILTERS["max_dev_holding"]:
            return False, f"Dev holdings too high: {dev_holdings:.1f}%"

        # 6. Creator count check
        if len(creators) > 1:
            return False, f"Too many creators: {len(creators)}"

        # 7. Safety checks
        if freeze_authority:
            return False, f"Freeze authority not revoked"
        if update_authority:
            return False, f"Update authority not revoked"
        if is_mutable:
            return False, f"Token is still mutable"

        # 8. Distribution check
        if holder_concentration > 0.5:
            return False, f"Top holders control too much supply: {holder_concentration:.1%}"

        return True, "Passed all filters"

    except Exception as e:
        print(f"[ERROR] Filter logic failed: {e}")
        return False, f"Filter error: {e}"
async def analyze_token(session, mint):
    """Analyze a single token and apply filters"""
    try:
        print(f"[INFO] Analyzing token: {mint}")
        
        # Fetch data from both APIs
        birdeye_task = get_birdeye_data(session, mint)
        metadata_task = get_token_metadata(session, mint)
        
        birdeye_data, metadata = await asyncio.gather(birdeye_task, metadata_task)

        # Apply filters
        passed, reason = apply_graduated_filters(birdeye_data, metadata)
        
        if not passed:
            print(f"[FILTER] {mint} rejected: {reason}")
            return None

        # Build result
        token_data = {
            "mint": mint,
            "name": birdeye_data.get("name", "Unnamed"),
            "symbol": birdeye_data.get("symbol", ""),
            "price": birdeye_data.get("price_usd", 0),
            "volume": birdeye_data.get("volume24h", 0),
            "market_cap": birdeye_data.get("mc", 0),
            "ath": birdeye_data.get("ath", 0),
            "liquidity": birdeye_data.get("liquidity", 0),
            "dev_holdings": metadata.get("token_info", {}).get("creator_token_holdings", 0),
            "creators_count": len(metadata.get("creators", [])),
            "reason": reason
        }
        
        print(f"[PASS] {mint} ({token_data['name']}) - ${token_data['market_cap']:,.0f} MC")
        return token_data
        
    except Exception as e:
        print(f"[ERROR] Token {mint} analysis failed: {e}")
        return None

async def check_graduated_tokens():
    """Main function to check for graduated tokens"""
    print("🔍 Querying Bitquery for graduated tokens...")
    
    try:
        # Get time range
        time_start, time_end = get_time_range(minutes_back=60, min_seconds_ago=30)
        print(f"[INFO] Searching from {time_start} to {time_end}")
        
        # Build query with time variables (string replacement)
        query_with_vars = GRADUATION_QUERY.replace("$time_start", time_start).replace("$time_end", time_end)
        
        # ✅ FIXED - Properly await the async call_bitquery_api function
        response = await call_bitquery_api(query_with_vars)
        
        if response is None:
            print("[ERROR] Bitquery returned None response")
            return []

        # Extract mint addresses
        mints = extract_mints_from_response(response)
        
        if not mints:
            print("[INFO] No graduated tokens found in time range")
            return []
            
        print(f"[INFO] Found {len(mints)} potential graduated tokens")

        # Analyze tokens concurrently with rate limiting
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=10)  # Limit concurrent connections
        ) as session:
            
            # Process tokens in batches to avoid rate limits
            batch_size = 5
            all_results = []
            
            for i in range(0, len(mints), batch_size):
                batch = mints[i:i + batch_size]
                print(f"[INFO] Processing batch {i//batch_size + 1}/{(len(mints)-1)//batch_size + 1}")
                
                tasks = [analyze_token(session, mint) for mint in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out None results and exceptions
                valid_results = [
                    r for r in batch_results 
                    if r is not None and not isinstance(r, Exception)
                ]
                all_results.extend(valid_results)
                
                # Small delay between batches
                if i + batch_size < len(mints):
                    await asyncio.sleep(0.5)

        graduated_tokens = all_results
        print(f"✅ {len(graduated_tokens)} graduated tokens passed all filters")
        
        # Print summary
        if graduated_tokens:
            print("\n🎯 GRADUATED TOKENS FOUND:")
            for token in graduated_tokens:
                print(f"  • {token['name']} ({token['symbol']}) - ${token['market_cap']:,.0f} MC")
        
        return graduated_tokens

    except Exception as e:
        print(f"[ERROR] check_graduated_tokens failed: {e}")
        import traceback
        traceback.print_exc()
        return []
# ✅ Test function
async def test_graduation_check():
    """Test function to verify graduation detection"""
    print("🧪 Testing graduation detection...")
    tokens = await check_graduated_tokens()
    print(f"✅ Test complete. Found {len(tokens)} graduated tokens.")
    return tokens

# Optional direct execution
if __name__ == "__main__":
    asyncio.run(test_graduation_check())
