# filters/initial_checks.py

import datetime
from config import INITIAL_FILTERS
from bitquery_api import call_bitquery_api


BITQUERY_NEW_TOKENS_QUERY = """
query NewTokens {
  solana {
    tokens(
      limit: 50
      order_by: {block: {height: desc}}
      where: {
        mint_timestamp: {since: "10 minutes"}
        update_authority: {is_not: null}
      }
    ) {
      address
      name
      symbol
      mint_timestamp
      update_authority
      supply
    }
  }
}
"""


async def fetch_new_tokens():
    try:
        result = call_bitquery_api(BITQUERY_NEW_TOKENS_QUERY)
        if not result or "data" not in result:
            print("[ERROR] Invalid Bitquery response.")
            return []

        tokens = result["data"]["solana"]["tokens"]
        new_tokens = []

        for t in tokens:
            new_tokens.append({
                "mint": t["address"],
                "name": t.get("name", "Unnamed"),
                "symbol": t.get("symbol", ""),
                "created_at": t["mint_timestamp"],
                "deployer": t["update_authority"],
                "supply": t["supply"],
                # placeholders for compatibility with existing filters:
                "marketCap": 0,
                "holderCount": 0,
                "volume24h": 0,
                "devHoldingPercent": 0,
                "buyCount24h": 0,
                "socials": [],
            })

        return new_tokens

    except Exception as e:
        print(f"[ERROR] Bitquery fetch failed: {e}")
        return []


def apply_filters(token):
    try:
        market_cap = token.get("marketCap", 0)
        holders = token.get("holderCount", 0)
        volume = token.get("volume24h", 0)
        dev_percent = token.get("devHoldingPercent", 100)
        buys = token.get("buyCount24h", 0)
        socials = token.get("socials", [])

        if market_cap < INITIAL_FILTERS["market_cap_min"]:
            return False
        if holders < INITIAL_FILTERS["min_holders"]:
            return False
        if volume < INITIAL_FILTERS["volume_min"]:
            return False
        if dev_percent > INITIAL_FILTERS["dev_max_percent"]:
            return False
        if buys < INITIAL_FILTERS["min_buys"]:
            return False
        if len(socials) < INITIAL_FILTERS["min_socials"]:
            return False

        return True
    except Exception as e:
        print(f"[ERROR] Filtering token failed: {e}")
        return False


async def check_new_tokens():
    raw_tokens = await fetch_new_tokens()
    filtered_tokens = [t for t in raw_tokens if apply_filters(t)]
    print(f"[INFO] New Tokens Passed Initial Filters: {len(filtered_tokens)}")
    return filtered_tokens
