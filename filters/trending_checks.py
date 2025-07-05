import aiohttp
import asyncio
from config import BIRDEYE_API_KEY, TRENDING_FILTERS

BIRDEYE_TRENDING_URL = "https://public-api.birdeye.so/public/token/trending-token"


async def fetch_trending_tokens():
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY
    }
    params = {
        "timeframe": "1m"  # 1-minute trending timeframe
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(BIRDEYE_TRENDING_URL, headers=headers, params=params) as resp:
            if resp.status != 200:
                print(f"[ERROR] Failed to fetch trending tokens: {resp.status}")
                return []
            data = await resp.json()
            return data.get("data", [])


def apply_trending_filters(token):
    try:
        liquidity = token.get("liquidity", 0)
        volume_1m = token.get("volume_1m", 0)
        market_cap = token.get("market_cap", 0)

        if liquidity < TRENDING_FILTERS["liquidity_min"]:
            return False
        if volume_1m < TRENDING_FILTERS["volume_1min"]:
            return False
        min_cap, max_cap = TRENDING_FILTERS["market_cap_range"]
        if not (min_cap <= market_cap <= max_cap):
            return False

        return True
    except Exception as e:
        print(f"[ERROR] Trending filter failed: {e}")
        return False


async def check_trending_tokens():
    tokens = await fetch_trending_tokens()
    passed = [t for t in tokens if apply_trending_filters(t)]
    print(f"[INFO] Trending Tokens Passed Filters: {len(passed)}")
    return passed


# For testing
if __name__ == "__main__":
    result = asyncio.run(check_trending_tokens())
    for token in result:
        print(token.get("symbol"), token.get("address"))
