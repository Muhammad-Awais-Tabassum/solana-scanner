import aiohttp
import asyncio
from config import HELIUS_API_KEY, HELIUS_BASE_URL, INITIAL_FILTERS

# filters/initial_checks.py

from config import INITIAL_FILTERS
import requests

def run_initial_checks(token_data: dict) -> bool:
    """
    Apply basic filtering rules to new tokens.
    """
    try:
        if token_data.get("liquidity", 0) < INITIAL_FILTERS["min_liquidity"]:
            return False
        if token_data.get("deployer_token_count", 0) > INITIAL_FILTERS["max_deployer_tokens"]:
            return False
        if token_data.get("age_minutes", 0) < INITIAL_FILTERS["min_age_minutes"]:
            return False
        if token_data.get("market_cap", 0) > INITIAL_FILTERS["max_market_cap"]:
            return False
        if token_data.get("volume_5m", 0) < INITIAL_FILTERS["min_volume_5m"]:
            return False
        return True
    except Exception as e:
        print(f"[initial_checks] Error in check: {e}")
        return False
async def fetch_new_tokens():
    url = f"{HELIUS_BASE_URL}tokens?api-key={HELIUS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[ERROR] Failed to fetch tokens: {resp.status}")
                return []
            data = await resp.json()
            return data.get("tokens", [])


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


# For testing
if __name__ == "__main__":
    result = asyncio.run(check_new_tokens())
    for token in result:
        print(token["address"], token.get("name", "Unnamed"))
