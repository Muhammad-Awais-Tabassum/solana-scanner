# utils/api_helpers.py

import aiohttp
import asyncio
import os
import logging
from functools import lru_cache
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")YE_API_KEY = os.getenv("BIRDEYE_API_KEY")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")


# ---------- Helius: Generic Fetcher ----------
async def fetch_helius_data(endpoint: str, params: dict = None) -> dict:
    """
    Makes an async GET request to a Helius API endpoint.
    """
    base_url = "https://api.helius.xyz/v0/"
    url = f"{base_url}{endpoint}?api-key={HELIUS_API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logging.error(f"[HELIUS] Fetch failed: {resp.status}")
                return {}
            return await resp.json()


# ---------- Helius: Token Holders ----------
async def get_token_holders(token_address: str) -> list[dict]:
    endpoint = f"tokens/holders"
    params = {"tokenAddress": token_address}
    data = await fetch_helius_data(endpoint, params)
    return data.get("holders", [])


# ---------- Birdeye: Token Price History ----------
async def fetch_price_history_birdeye(token_address: str) -> list[tuple[str, float]]:
    url = f"https://public-api.birdeye.so/defi/token_price_chart?address={token_address}&type=5m"
    headers = {"X-API-KEY": BIRDEYE_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if "data" in data and "items" in data["data"]:
                return [(i["time"], i["value"]) for i in data["data"]["items"]]
    return []


# ---------- Birdeye: Metadata (MC, Liquidity, Volume) ----------
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


def get_post_dump_buyers(token_address: str, dump_time: datetime = None) -> dict:
    """
    Fetches new wallet buyers of a token post-dump using Helius API.
    Filters for buys with 2–3 SOL.
    """

    # Safety check
    if not dump_time:
        dump_time = datetime.utcnow() - timedelta(minutes=30)  # fallback: last 30min

    url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    # Helius: get token transfer history
    payload = {
        "jsonrpc": "2.0",
        "id": "fetch-transfers",
        "method": "searchTransactions",
        "params": {
            "query": {
                "account": token_address,
                "type": "transfer",
            },
            "options": {
                "limit": 100,
                "sort": "desc"
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return {"count": 0, "avg_sol": 0.0}

    txs = response.json().get("result", [])
    buyers = {}
    
    for tx in txs:
        ts = tx.get("timestamp")
        if not ts or datetime.utcfromtimestamp(ts) < dump_time:
            continue

        # Only look at post-dump buys
        transfers = tx.get("tokenTransfers", [])
        for tr in transfers:
            if tr.get("mint") != token_address:
                continue

            buyer = tr.get("toUserAccount")
            sol_spent = tx.get("fee", 0) / 1e9  # fallback: use fee as rough SOL proxy

            if buyer not in buyers:
                buyers[buyer] = sol_spent
            else:
                buyers[buyer] += sol_spent

    # Filter wallets spending 2–3 SOL
    filtered = [amt for amt in buyers.values() if 2 <= amt <= 3]
    count = len(filtered)
    avg_sol = round(sum(filtered) / count, 4) if count else 0.0

    return {"count": count, "avg_sol": avg_sol}
# ---------- Simple Rate Limit Delay ----------
async def rate_limited_request():
    await asyncio.sleep(0.2)  # 5 requests/sec (Helius and Birdeye safe zone)
