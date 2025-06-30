# utils/api_helpers.py

import aiohttp
import asyncio
import os
import logging
from functools import lru_cache
from datetime import datetime, timedelta

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

# ---------- Birdeye: Price History ----------
async def get_birdeye_price_history(token_address: str) -> list[tuple[str, float]]:
    url = f"https://public-api.birdeye.so/defi/token_price_chart?address={token_address}&type=5m"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if "data" in data and "items" in data["data"]:
                return [(i["time"], i["value"]) for i in data["data"]["items"]]
    return []

# ---------- Helius: Token Holders ----------
async def get_token_holders(token_address: str) -> list[dict]:
    url = f"https://api.helius.xyz/v0/tokens/holders?api-key={HELIUS_API_KEY}&tokenAddress={token_address}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get("holders", [])

# ---------- Metadata from Birdeye (MC, Liquidity, Volume) ----------
async def get_token_metadata(token_address: str) -> dict:
    url = f"https://public-api.birdeye.so/public/token/{token_address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if "data" in data:
                return {
                    "marketCap": data["data"].get("market_cap", 0),
                    "liquidity": data["data"].get("liquidity", 0),
                    "volume": data["data"].get("volume_24h", 0),
                }
    return {}

# ---------- Rate Limiting (simple delay) ----------
async def rate_limit_delay():
    await asyncio.sleep(0.2)  # 5 requests per second