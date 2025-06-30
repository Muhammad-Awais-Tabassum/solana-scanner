import asyncio
from utils.api_helpers import fetch_helius_data
import json

# Thresholds for deployer disqualification
FAILURE_RATE_THRESHOLD = 0.97
SUCCESS_MC_THRESHOLD = 3_000_000  # $3M
FAIL_MC_THRESHOLD = 200_000       # $200K

async def get_deployer_tokens(deployer_address: str):
    # Uses Helius Enhanced API to fetch tokens deployed by the same address
    url = f"https://api.helius.xyz/v0/addresses/{deployer_address}/tokens?type=created"
    data = await fetch_helius_data(url)
    return data.get("tokens", [])

async def analyze_deployer_history(deployer_address: str) -> dict:
    tokens = await get_deployer_tokens(deployer_address)
    
    total_tokens = len(tokens)
    successful = 0
    failed = 0

    for token in tokens:
        try:
            market_cap = token.get("marketCap", 0)
            if market_cap >= SUCCESS_MC_THRESHOLD:
                successful += 1
            elif market_cap < FAIL_MC_THRESHOLD:
                failed += 1
        except Exception:
            continue

    # Handle divide by zero case
    if total_tokens == 0:
        return {"qualified": True, "reason": "No history"}

    fail_rate = failed / total_tokens

    if fail_rate >= FAILURE_RATE_THRESHOLD:
        return {
            "qualified": False,
            "reason": f"Failure rate too high ({fail_rate*100:.1f}%) across {total_tokens} tokens"
        }

    return {
        "qualified": True,
        "reason": f"{successful}/{total_tokens} tokens reached > $3M or avoided early failure"
    }