import aiohttp
import asyncio
from datetime import datetime, timedelta
from config import GRADUATED_FILTERS, HELIUS_API_KEY, HELIUS_BASE_URL


async def fetch_graduated_tokens():
    url = f"{HELIUS_BASE_URL}graduated-tokens?api-key={HELIUS_API_KEY}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[ERROR] Failed to fetch graduated tokens: {resp.status}")
                return []
            data = await resp.json()
            return data.get("tokens", [])


def has_dipped_from_ath(token):
    try:
        ath = token.get("ath", 0)
        current = token.get("price", 0)
        if ath == 0:
            return False
        dip_percent = ((ath - current) / ath) * 100
        return dip_percent >= GRADUATED_FILTERS["price_dip_pct"]
    except:
        return False


def check_volume_spike(token):
    vol_5min = token.get("volume5m", 0)
    return vol_5min >= GRADUATED_FILTERS["recent_volume_5m"]


def check_new_wallets(token):
    buyers = token.get("recentBuyers", [])
    for buyer in buyers:
        if buyer.get("isNew") and buyer.get("amount", 0) in GRADUATED_FILTERS["min_new_wallet_sol"]:
            return True
    return False


def apply_graduated_filters(token):
    try:
        market_cap = token.get("marketCap", 0)
        volume = token.get("volume24h", 0)
        dev_percent = token.get("devHoldingPercent", 100)
        insider_percent = token.get("insiderPercent", 100)
        socials = token.get("socials", [])

        if market_cap < GRADUATED_FILTERS["market_cap_min"]:
            return False
        if volume < GRADUATED_FILTERS["volume_min"]:
            return False
        if dev_percent > GRADUATED_FILTERS["dev_max_percent"]:
            return False
        if insider_percent > GRADUATED_FILTERS["insider_max_percent"]:
            return False
        if len(socials) < GRADUATED_FILTERS["min_socials"]:
            return False

        # Advanced checks (must fulfill all)
        if not check_volume_spike(token):
            return False
        if not has_dipped_from_ath(token):
            return False
        if not check_new_wallets(token):
            return False

        return True
    except Exception as e:
        print(f"[ERROR] Graduated filter failed: {e}")
        return False


async def check_graduated_tokens():
    tokens = await fetch_graduated_tokens()
    passed = [t for t in tokens if apply_graduated_filters(t)]
    print(f"[INFO] Graduated Tokens Passed Filters: {len(passed)}")
    return passed
analyze_graduated_tokens = check_graduated_tokens

# For testing
if __name__ == "__main__":
    result = asyncio.run(check_graduated_tokens())
    for token in result:
        print(token["address"], token.get("name", "Unnamed"))
