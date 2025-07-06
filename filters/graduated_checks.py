import aiohttp
import asyncio
from config import (
    GRADUATED_FILTERS,
    BIRDEYE_API_KEY,
    SHYFT_API_KEY,
)

PUMPFUN_LAUNCHES = "https://pump.fun/api/launches"
PUMPFUN_TOKEN_API = "https://pump.fun/api/token/"
BIRDEYE_TOKEN_INFO = "https://public-api.birdeye.so/public/token/"
SHYFT_METADATA_URL = "https://api.shyft.to/sol/v1/token/get_info?network=mainnet&token="

HEADERS_BIRDEYE = {"X-API-KEY": BIRDEYE_API_KEY}
HEADERS_SHYFT = {"x-api-key": SHYFT_API_KEY}


async def fetch_recent_pumpfun_tokens(session):
    async with session.get(PUMPFUN_LAUNCHES) as resp:
        if resp.status != 200:
            print("[ERROR] Failed to fetch Pump.fun launches")
            return []
        data = await resp.json()
        return [t["mint"] for t in data.get("launchedTokens", [])]


async def is_graduated_pumpfun(session, mint):
    async with session.get(PUMPFUN_TOKEN_API + mint) as resp:
        return resp.status == 404


async def get_birdeye_data(session, mint):
    async with session.get(BIRDEYE_TOKEN_INFO + mint, headers=HEADERS_BIRDEYE) as resp:
        if resp.status != 200:
            return {}
        data = await resp.json()
        return data.get("data", {})


async def get_token_metadata(session, mint):
    async with session.get(SHYFT_METADATA_URL + mint, headers=HEADERS_SHYFT) as resp:
        if resp.status != 200:
            return {}
        result = await resp.json()
        return result.get("result", {})


def apply_graduated_filters(birdeye_data, metadata):
    try:
        market_cap = birdeye_data.get("mc", 0)
        volume = birdeye_data.get("volume24h", 0)
        price = birdeye_data.get("price_usd", 0)
        ath = birdeye_data.get("ath", price)

        dev_holdings = metadata.get("token_info", {}).get("creator_token_holdings", 100)
        creators = metadata.get("creators", [])

        if market_cap < GRADUATED_FILTERS["market_cap_min"]:
            return False
        if volume < GRADUATED_FILTERS["volume_min"]:
            return False
        if ath != 0:
            dip = ((ath - price) / ath) * 100
            if dip < GRADUATED_FILTERS["price_dip_pct"]:
                return False
        if dev_holdings > GRADUATED_FILTERS["dev_max_percent"]:
            return False
        if creators and len(creators) > 1:
            return False  # Optional: discourage multiple creators
        return True
    except Exception as e:
        print(f"[ERROR] Filter logic failed: {e}")
        return False


async def analyze_token(session, mint):
    try:
        graduated = await is_graduated_pumpfun(session, mint)
        if not graduated:
            return None  # Still on Pump.fun

        birdeye_data = await get_birdeye_data(session, mint)
        metadata = await get_token_metadata(session, mint)

        if not apply_graduated_filters(birdeye_data, metadata):
            return None

        return {
            "mint": mint,
            "name": birdeye_data.get("name", "Unnamed"),
            "price": birdeye_data.get("price_usd"),
            "volume": birdeye_data.get("volume24h"),
            "market_cap": birdeye_data.get("mc"),
        }
    except Exception as e:
        print(f"[ERROR] Token {mint} failed: {e}")
        return None


async def check_graduated_tokens():
    async with aiohttp.ClientSession() as session:
        pumpfun_tokens = await fetch_recent_pumpfun_tokens(session)
        tasks = [analyze_token(session, mint) for mint in pumpfun_tokens]
        results = await asyncio.gather(*tasks)
        graduated = [r for r in results if r]
        print(f"[INFO] Graduated Tokens Detected: {len(graduated)}")
        return graduated


# For testing
if __name__ == "__main__":
    asyncio.run(check_graduated_tokens())
