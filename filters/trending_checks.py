import aiohttp import asyncio import logging from config import HELIUS_API_KEY, BIRDEYE_API_KEY, SHYFT_API_KEY, TRENDING_FILTERS from filters.extra_heuristics import apply_extra_heuristics from utils.api_helpers import get_token_holders

HELIUS_NEW_TOKENS_URL = f"https://api.helius.xyz/v0/tokens/recent?api-key={HELIUS_API_KEY}" BIRDEYE_TOKEN_INFO_URL = "https://public-api.birdeye.so/public/token/{}"

async def fetch_new_tokens(): async with aiohttp.ClientSession() as session: async with session.get(HELIUS_NEW_TOKENS_URL) as resp: if resp.status != 200: print(f"[ERROR] Helius token fetch failed: {resp.status}") return [] data = await resp.json() return [token['mint'] for token in data.get("tokens", [])]

async def fetch_token_metrics(session, address): url = BIRDEYE_TOKEN_INFO_URL.format(address) headers = {"X-API-KEY": BIRDEYE_API_KEY} try: async with session.get(url, headers=headers) as resp: if resp.status != 200: return None data = await resp.json() return data.get("data", {}) except Exception as e: print(f"[ERROR] Failed to fetch token metrics for {address}: {e}") return None

def compute_trending_score(token): try: price_change = token.get("price_change_5m", 0) volume = token.get("volume_5m", 0) liquidity = token.get("liquidity", 0) holders = token.get("holders", 0)

score = 0.4 * price_change + 0.3 * (volume / 1000) + 0.2 * (liquidity / 100) + 0.1 * (holders / 10)
    return score
except Exception as e:
    print(f"[ERROR] Scoring error: {e}")
    return 0

def apply_filters(token): if token.get("liquidity", 0) < TRENDING_FILTERS["liquidity_min"]: return False if token.get("volume_5m", 0) < TRENDING_FILTERS["volume_5m"]: return False cap_range = TRENDING_FILTERS["market_cap_range"] if not (cap_range[0] <= token.get("market_cap", 0) <= cap_range[1]): return False return True

async def scan_trending_tokens(): new_tokens = await fetch_new_tokens() print(f"[INFO] Found {len(new_tokens)} new tokens to scan.") trending = []

async with aiohttp.ClientSession() as session:
    tasks = [fetch_token_metrics(session, addr) for addr in new_tokens]
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

        # Fetch holder count from SHYFT holders API
        holders = await get_token_holders(session, new_tokens[i])
        token_data["holders"] = len(holders)

        # Apply filters and heuristics
        if apply_filters(token_data) and await apply_extra_heuristics(session, token_data):
            token_data["score"] = compute_trending_score(token_data)
            trending.append(token_data)

trending_sorted = sorted(trending, key=lambda x: x["score"], reverse=True)
print(f"[INFO] {len(trending_sorted)} tokens passed filters + heuristics. Top 5:")
for t in trending_sorted[:5]:
    print(f"{t['symbol']} | Score: {t['score']:.2f} | Address: {t['address']}")

return trending_sorted[:5]

if name == "main": asyncio.run(scan_trending_tokens())

