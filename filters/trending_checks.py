import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
import json

from config import BITQUERY_AUTH_TOKEN, TRENDING_FILTERS
from filters.extra_heuristics import apply_extra_heuristics
from utils.api_helpers import get_token_holders

# Bitquery GraphQL endpoint
BITQUERY_URL = "https://streaming.bitquery.io/graphql"

async def fetch_trending_tokens_bitquery():
    """Fetch trending tokens using Bitquery GraphQL"""
    
    # Calculate time 1 hour ago
    time_1h_ago = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    query = """
    query ComprehensiveTrending($time_1h_ago: DateTime) {
      Solana {
        DEXTradeByTokens(
          where: {
            Transaction: { Result: { Success: true } }
            Block: { Time: { since: $time_1h_ago } }
            any: [
              {
                Trade: {
                  Side: {
                    Currency: {
                      MintAddress: {
                        is: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                      }
                    }
                  }
                }
              }
              {
                Trade: {
                  Currency: {
                    MintAddress: {
                      not: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                    }
                  }
                  Side: {
                    Currency: {
                      MintAddress: {
                        is: "So11111111111111111111111111111111111111112"
                      }
                    }
                  }
                }
              }
            ]
          }
          orderBy: { descendingByField: "trades_count_1h" }
          limit: { count: 50 }
        ) {
          Trade {
            Currency {
              Symbol
              Name
              MintAddress
            }
            Latest_Price: PriceInUSD(maximum: Block_Time)
          }
          makers: count(distinct: Transaction_Signer)
          buyers: count(distinct: Transaction_Signer, if: { Trade: { Side: { Type: { is: buy } } } })
          sellers: count(distinct: Transaction_Signer, if: { Trade: { Side: { Type: { is: sell } } } })
          traded_volume: sum(of: Trade_Side_AmountInUSD)
          buy_volume: sum(of: Trade_Side_AmountInUSD, if: { Trade: { Side: { Type: { is: buy } } } })
          sell_volume: sum(of: Trade_Side_AmountInUSD, if: { Trade: { Side: { Type: { is: sell } } } })
          buys: count(if: { Trade: { Side: { Type: { is: buy } } } })
          sells: count(if: { Trade: { Side: { Type: { is: sell } } } })
          trades_count_1h: count
        }
      }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BITQUERY_AUTH_TOKEN}"
    }
    
    payload = {
        "query": query,
        "variables": {
            "time_1h_ago": time_1h_ago
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(BITQUERY_URL, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    print(f"[ERROR] Bitquery API failed: {resp.status}")
                    return []
                
                data = await resp.json()
                if "errors" in data:
                    print(f"[ERROR] GraphQL errors: {data['errors']}")
                    return []
                
                return data.get("data", {}).get("Solana", {}).get("DEXTradeByTokens", [])
                
        except Exception as e:
            print(f"[ERROR] Bitquery request failed: {e}")
            return []

def transform_bitquery_data(bitquery_token):
    """Convert Bitquery response to your existing token_data format"""
    try:
        trade_data = bitquery_token.get("Trade", {})
        currency = trade_data.get("Currency", {})
        
        # Calculate metrics from Bitquery data
        traded_volume = bitquery_token.get("traded_volume", 0)
        buy_volume = bitquery_token.get("buy_volume", 0)
        sell_volume = bitquery_token.get("sell_volume", 0)
        buyers = bitquery_token.get("buyers", 0)
        sellers = bitquery_token.get("sellers", 0)
        latest_price = trade_data.get("Latest_Price", 0)
        
        # Calculate price change approximation (buy/sell pressure)
        buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else float('inf')
        price_change_5m = min(buy_sell_ratio * 10, 100)  # Cap at 100%
        
        # Estimate market cap (assuming 1B token supply - adjust as needed)
        estimated_supply = 1_000_000_000
        market_cap = latest_price * estimated_supply if latest_price else 0
        
        return {
            "address": currency.get("MintAddress", ""),
            "symbol": currency.get("Symbol", "Unknown"),
            "name": currency.get("Name", "Unknown"),
            "price_change_5m": price_change_5m,
            "volume_5m": traded_volume,
            "liquidity": traded_volume * 2,  # Rough liquidity estimate
            "market_cap": market_cap,
            "latest_price": latest_price,
            
            # Rich Bitquery metrics
            "buyers": buyers,
            "sellers": sellers,
            "makers": bitquery_token.get("makers", 0),
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "buy_sell_ratio": buy_sell_ratio,
            "total_trades": bitquery_token.get("trades_count_1h", 0),
            "buys": bitquery_token.get("buys", 0),
            "sells": bitquery_token.get("sells", 0)
        }
    except Exception as e:
        print(f"[ERROR] Data transformation error: {e}")
        return None


def compute_trending_score(token):
    """Enhanced scoring with Bitquery metrics"""
    try:
        # Original metrics
        price_change = token.get("price_change_5m", 0)
        volume = token.get("volume_5m", 0)
        liquidity = token.get("liquidity", 0)
        holders = token.get("holders", 0)
        
        # New Bitquery metrics
        buyers = token.get("buyers", 0)
        buy_sell_ratio = token.get("buy_sell_ratio", 1)
        total_trades = token.get("total_trades", 0)
        makers = token.get("makers", 0)

        # Enhanced scoring algorithm
        score = (
            0.25 * price_change +                    # Price momentum
            0.25 * (volume / 1000) +                 # Volume
            0.15 * (liquidity / 100) +               # Liquidity  
            0.10 * (holders / 10) +                  # Holder count
            0.10 * (buyers / 5) +                    # Unique buyers
            0.10 * min(buy_sell_ratio, 5) +          # Buy pressure (capped)
            0.05 * (total_trades / 10)               # Trading activity
        )
        
        return score
    except Exception as e:
        print(f"[ERROR] Scoring error: {e}")
        return 0

def apply_enhanced_filters(token):
    """Enhanced filters using Bitquery data"""
    try:
        # Original filters
        if token.get("liquidity", 0) < TRENDING_FILTERS["liquidity_min"]:
            return False
        if token.get("volume_5m", 0) < TRENDING_FILTERS["volume_5m"]:
            return False
        
        cap_range = TRENDING_FILTERS["market_cap_range"]
        if not (cap_range[0] <= token.get("market_cap", 0) <= cap_range[1]):
            return False
        
        # New Bitquery-based filters
        if token.get("buyers", 0) < 10:  # At least 10 unique buyers
            return False
            
        if token.get("buyers", 0) <= token.get("sellers", 0):  # More buyers than sellers
            return False
            
        if token.get("buy_sell_ratio", 0) < 1.2:  # Strong buy pressure
            return False
            
        if token.get("total_trades", 0) < 20:  # Minimum trading activity
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Filter error: {e}")
        return False


async def scan_trending_tokens():
    """Main trending scan function using Bitquery"""
    print("[INFO] Fetching trending tokens from Bitquery...")
    
    bitquery_tokens = await fetch_trending_tokens_bitquery()
    print(f"[INFO] Found {len(bitquery_tokens)} trending tokens from Bitquery.")
    
    if not bitquery_tokens:
        print("[WARNING] No tokens returned from Bitquery")
        return []
    
    trending = []
    
    async with aiohttp.ClientSession() as session:
        for bitquery_token in bitquery_tokens:
            # Transform Bitquery data to your format
            token_data = transform_bitquery_data(bitquery_token)
            if not token_data:
                continue
            
            # Add holder count (keep your existing SHYFT integration)
            try:
                holders = await get_token_holders(session, token_data["address"])
                token_data["holders"] = len(holders) if holders else 0
            except Exception as e:
                print(f"[WARNING] Could not fetch holders for {token_data['address']}: {e}")
                token_data["holders"] = 0
            
            # Apply enhanced filters and heuristics
            if apply_enhanced_filters(token_data) and await apply_extra_heuristics(session, token_data):
                token_data["score"] = compute_trending_score(token_data)
                trending.append(token_data)
                
                print(f"[PASS] {token_data['symbol']} | "
                      f"Buyers: {token_data['buyers']} | "
                      f"B/S Ratio: {token_data['buy_sell_ratio']:.2f} | "
                      f"Volume: ${token_data['volume_5m']:,.0f}")

    # Sort by score
    trending_sorted = sorted(trending, key=lambda x: x["score"], reverse=True)
    
    print(f"\n[INFO] {len(trending_sorted)} tokens passed enhanced filters. Top 5:")
    for i, t in enumerate(trending_sorted[:5], 1):
        print(f"{i}. {t['symbol']} ({t['name'][:20]}...)")
        print(f"   Score: {t['score']:.2f} | Address: {t['address']}")
        print(f"   Buyers: {t['buyers']} | Sellers: {t['sellers']} | B/S: {t['buy_sell_ratio']:.2f}")
        print(f"   Volume: ${t['volume_5m']:,.0f} | Market Cap: ${t['market_cap']:,.0f}")
        print(f"   Trades: {t['total_trades']} | Price: ${t['latest_price']:.8f}")
        print()

    return trending_sorted[:5]


# For testing or standalone usage
if __name__ == "__main__":
    asyncio.run(scan_trending_tokens())
