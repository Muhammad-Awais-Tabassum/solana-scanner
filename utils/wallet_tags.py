# utils/wallet_tags.py

import json

# Load your known sniper/insider list
with open("data/wallet_tags.json", "r") as f:
    WALLET_TAGS = json.load(f)

def is_sniper(wallet: str) -> bool:
    return WALLET_TAGS.get(wallet, "") == "sniper"

def is_insider(wallet: str) -> bool:
    return WALLET_TAGS.get(wallet, "") == "insider"

def get_wallet_tag(wallet: str) -> str:
    return WALLET_TAGS.get(wallet, "unknown")