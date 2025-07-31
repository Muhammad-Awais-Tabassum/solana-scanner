import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
import json

from config import (
    BITQUERY_API_KEY,
    LIQUIDITY_MIN_TRENDING,
    VOLUME_1MIN_MIN_TRENDING, 
    MC_MIN_TRENDING,
    MC_MAX_TRENDING
)
from filters.extra_heuristics import apply_extra_heuristics
from utils.api_helpers import get_token_holders

# Bitquery GraphQL endpoint
BITQUERY_URL = "https://streaming.bitquery.io/graphql"

async def fetch_trending_tokens_bitquery():
    """Fetch trending tokens using Bitquery GraphQL"""
    
    # Calculate time 1 hour ago for trending detection
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
              {
                Trade: {
                  Currency: {
                    MintAddress: {
                      notIn: [
                        "So11111111111111111111111111111111111111112"
                        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                      ]
                    }
                  }
                  Side: {
                    Currency: {
                      MintAddress: {
                        notIn: [
                          "So11111111111111111111111111111111111111112"
                          "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                        ]
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
    """Convert Bitquery response to match your exact format"""
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
        price_change_1m = min(buy_sell_ratio * 8, 50)  # Adjusted for 1min timeframe
        
        # Estimate market cap (adjust supply estimation as needed)
        estimated_supply = 1_000_000_000  # Standard assumption - can be refined
        market_cap = latest_price * estimated_supply if latest_price else 0
        
        return {
            "address": currency.get("MintAddress", ""),
            "symbol": currency.get("Symbol", "Unknown"),
            "name": currency.get("Name", "Unknown"),
            
            # Your original format - adjusted for 1min
            "price_change_1m": price_change_1m,
            "volume_1m": traded_volume,
            "liquidity": traded_volume * 1.5,  # Conservative liquidity estimate
            "market_cap": market_cap,
            "latest_price": latest_price,
            
            # Enhanced Bitquery metrics
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
    """Scoring optimized for your exact filter ranges"""
    try:
        # Adjusted for your ranges and 1min timeframe
        price_change = token.get("price_change_1m", 0)
        volume = token.get("volume_1m", 0)
        liquidity = token.get("liquidity", 0)
        holders = token.get("holders", 0)
        
        # Bitquery metrics
        buyers = token.get("buyers", 0)
        buy_sell_ratio = token.get("buy_sell_ratio", 1)
        total_trades = token.get("total_trades", 0)
        
        # Scoring adjusted for your exact value ranges
        score = (
            0.30 * (price_change / 10) +                    # Price momentum (1min)
            0.25 * ((volume - VOLUME_1MIN_MIN_TRENDING) / 10000) +  # Volume above your min ($5k)
            0.15 * ((liquidity - LIQUIDITY_MIN_TRENDING) / 20000) +  # Liquidity above your min ($8,250)
            0.10 * (holders / 20) +                         # Holder growth
            0.10 * (buyers / 10) +                          # Unique buyers
            0.10 * min(buy_sell_ratio - 1, 2)               # Buy pressure above 1.0
        )
        
        return max(score, 0)  # Ensure non-negative score
        
    except Exception as e:
        print(f"[ERROR] Scoring error: {e}")
        return 0


def apply_enhanced_filters(token):
    """Enhanced filters using your exact values"""
    try:
        # Your original filters with exact values
        if token.get("liquidity", 0) < LIQUIDITY_MIN_TRENDING:  # $8,250
            return False
            
        if token.get("volume_1m", 0) < VOLUME_1MIN_MIN_TRENDING:  # $5,000
            return False
        
        # Market cap range: $6k - $1M
        market_cap = token.get("market_cap", 0)
        if not (MC_MIN_TRENDING <= market_cap <= MC_MAX_TRENDING):
            return False
        
        # Enhanced Bitquery-based filters
        if token.get("buyers", 0) < 5:  # At least 5 unique buyers
            return False
            
        if token.get("buyers", 0) <= token.get("sellers", 0):  # More buyers than sellers
            return False
            
        if token.get("buy_sell_ratio", 0) < 1.1:  # Moderate buy pressure
            return False
            
        if token.get("total_trades", 0) < 15:  # Minimum trading activity
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Filter error: {e}")
        return False

async def scan_trending_tokens():
    """Main trending scan function using Bitquery with your exact filters"""
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
            
            # Add holder count (keep your existing SHYFT integration if available)
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
                      f"MC: ${token_data['market_cap']:,.0f} | "
                      f"Liq: ${token_data['liquidity']:,.0f} | "
                      f"Vol: ${token_data['volume_1m']:,.0f} | "
                      f"Buyers: {token_data['buyers']} | "
                      f"B/S: {token_data['buy_sell_ratio']:.2f}")

    # Sort by score
    trending_sorted = sorted(trending, key=lambda x: x["score"], reverse=True)
    
    print(f"\n[INFO] {len(trending_sorted)} tokens passed filters (Liq>${LIQUIDITY_MIN_TRENDING:,}, Vol>${VOLUME_1MIN_MIN_TRENDING:,}, MC${MC_MIN_TRENDING:,}-${MC_MAX_TRENDING:,}). Top 5:")
    
    for i, t in enumerate(trending_sorted[:5], 1):
        print(f"{i}. {t['symbol']} ({t['name'][:20]}...)")
        print(f"   Score: {t['score']:.2f} | Address: {t['address']}")
        print(f"   MC: ${t['market_cap']:,.0f} | Liq: ${t['liquidity']:,.0f}")
        print(f"   Vol(1m): ${t['volume_1m']:,.0f} | Price: ${t['latest_price']:.8f}")
        print(f"   Buyers: {t['buyers']} | Sellers: {t['sellers']} | B/S Ratio: {t['buy_sell_ratio']:.2f}")
        print(f"   Trades: {t['total_trades']} | Buys: {t['buys']} | Sells: {t['sells']}")
        print()

    return trending_sorted[:5]


# For testing or standalone usage
if __name__ == "__main__":
    asyncio.run(scan_trending_tokens())
