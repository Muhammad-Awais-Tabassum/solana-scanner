import logging
from utils.api_helpers import get_token_holders, get_token_metadata

async def check_top_holders_concentration(token_address: str, threshold: float = 0.25) -> bool:
    """
    Reject token if top 10 holders control more than 25% of total supply.
    """
    holders = await get_token_holders(token_address)
    if not holders or len(holders) < 10:
        return True  # Fail-safe if not enough data

    total_supply = sum([h["amount"] for h in holders])
    top_10 = sorted(holders, key=lambda h: h["amount"], reverse=True)[:10]
    top_10_total = sum([h["amount"] for h in top_10])
    return (top_10_total / total_supply) > threshold

async def detect_fake_volume_or_mc(token_address: str) -> bool:
    """
    Use metadata and heuristics to flag suspicious market cap or volume.
    """
    meta = await get_token_metadata(token_address)
    if not meta:
        return True

    volume = meta.get("volume", 0)
    market_cap = meta.get("marketCap", 0)
    liquidity = meta.get("liquidity", 0)

    if volume > 3 * liquidity and liquidity < 10_000:
        logging.warning("Fake volume suspected")
        return True

    if market_cap > 100_000 and liquidity < 5_000:
        logging.warning("Suspicious market cap")
        return True

    return False

def check_initial_supply_distribution(holders: list[dict]) -> bool:
    """
    Flags tokens where >2 wallets hold >8% each.
    """
    big_holders = [h for h in holders if h.get("percentage", 0) > 8]
    return len(big_holders) > 2

# ✅ Wrapper function for use in async main logic
async def apply_extra_heuristics(token: dict) -> bool:
    address = token.get("address")
    if not address:
        return False

    holders = await get_token_holders(address)
    if not holders:
        return False

    if await check_top_holders_concentration(address):
        return False

    if await detect_fake_volume_or_mc(address):
        return False

    if check_initial_supply_distribution(holders):
        return False

    return True
