# analyzer/wallet_analysis.py

import logging
from utils.api_helpers import get_token_holders
from utils.wallet_tags import is_sniper_wallet, is_insider_wallet

def analyze_wallets(token_address: str, deployer: str) -> dict:
    """
    Analyze token holder wallet behavior and structure.
    """
    holders = get_token_holders(token_address)
    analysis = {
        "total_holders": len(holders),
        "sniper_wallets": [],
        "insider_wallets": [],
        "deployer_sold": False,
        "high_concentration": False,
        "disqualified": False
    }

    sniper_count = 0
    insider_count = 0
    high_wallets = 0

    for h in holders:
        wallet = h["wallet"]
        pct = h.get("percentage", 0)

        if wallet == deployer and h.get("amount", 0) == 0:
            analysis["deployer_sold"] = True

        if is_sniper_wallet(wallet):
            sniper_count += 1
            analysis["sniper_wallets"].append(wallet)

        if is_insider_wallet(wallet):
            insider_count += 1
            analysis["insider_wallets"].append(wallet)

        if pct > 8:
            high_wallets += 1

    if sniper_count > 2 or insider_count > 2 or high_wallets > 2:
        analysis["disqualified"] = True

    return analysis