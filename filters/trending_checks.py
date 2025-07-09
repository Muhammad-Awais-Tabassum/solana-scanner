import aiohttp
import asyncio
import time
from datetime import datetime, timedelta
from config import HELIUS_API_KEY, BIRDEYE_API_KEY, SHYFT_API_KEY, TRENDING_FILTERS

HELIUS_NEW_TOKENS_URL = f"https://api.helius.xyz/v0/tokens/recent?api-key={HELIUS_API_KEY}"
BIRDEYE_TOKEN_INFO_URL = "https://public-api.birdeye.so/public/token/{}"
SHYFT_HOLDER_COUNT_URL = "https://shyft.to/sol/v1/token/holders?network=mainnet-beta&token={}"  # Optional

async def fetch_new_tokens():
    async with aiohttp.ClientSession() as session:
        async with session.get(HELIUS_NEW_TOKENS_URL) as resp:
            if resp.status != 200:
                print(f"[ERROR] Helius token fetch failed: {resp.status}")
                return []
            data = await resp.json()
            return [token['mint'] for token in data.get("tokens", [])]

async def fetch_token_metrics(session, address):
    url = BIRDEYE_TOKEN_INFO_URL.format(address)
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return data.get("data", {})
    except Exception as e:
        print(f"[ERROR] Failed to fetch token metrics for {address}: {e}")
        return None

async def fetch_holder_count(session, address):
    url = SHYFT_HOLDER_COUNT_URL.format(address)
    headers = {"x-api-key": SHYFT_API_KEY}
    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return 0
            data = await resp.json()
            return data.get("data", {}).get("total_holders", 0)
    except Exception as e:
        print(f"[ERROR] Failed to fetch holders for {address}: {e}")
        return 0

def compute_trending_score(token):
    try:
        price_change = token.get("price_change_5m", 0)
        volume = token.get("volume_5m", 0)
        liquidity = token.get("liquidity", 0)
        holders = token.get("holders", 0)

        score = 0.4 * price_change + 0.3 * (volume / 1000) + 0.2 * (liquidity / 100) + 0.1 * (holders / 10)
        return score
    except Exception as e:
        print(f"[ERROR] Scoring error: {e}")
        return 0

def apply_filters(token):
    if token.get("liquidity", 0) < TRENDING_FILTERS["liquidity_min"]:
        return False
    if token.get("volume_5m", 0) < TRENDING_FILTERS["volume_5m"]:
        return False
    cap_range = TRENDING_FILTERS["market_cap_range"]
    if not (cap_range[0] <= token.get("market_cap", 0) <= cap_range[1]):
        return False
    return True

async def scan_trending_tokens():
    new_tokens = await fetch_new_tokens()
    print(f"[INFO] Found {len(new_tokens)} new tokens to scan.")
    trending = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for addr in new_tokens:
            tasks.append(fetch_token_metrics(session, addr))
        raw_metrics = await asyncio.gather(*tasks)

        for i, metrics in enumerate(raw_metrics):
            if not metrics:
                continue

            token_data = {
                "address": new_tokens[i],
                "symbol": metrics.get("symbol"),
                "price_change_5m": metrics.get("price_change_5m", 0),
                "volume_5m": metrics.get("volume_5m", 0),
                "liquidity": metrics.get("liquidity", 0),
                "market_cap": metrics.get("market_cap", 0)
            }
            token_data["holders"] = await fetch_holder_count(session, new_tokens[i])

            if apply_filters(token_data):
                token_data["score"] = compute_trending_score(token_data)
                trending.append(token_data)

    trending_sorted = sorted(trending, key=lambda x: x["score"], reverse=True)
    print(f"[INFO] {len(trending_sorted)} tokens passed filters. Top 5:")
    for t in trending_sorted[:5]:
        print(f"{t['symbol']} | Score: {t['score']:.2f} | Address: {t['address']}")

    return trending_sorted[:5]

if __name__ == "__main__":
    asyncio.run(scan_trending_tokens())
