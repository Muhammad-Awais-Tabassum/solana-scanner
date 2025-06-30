# config.py

import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Helius API
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
HELIUS_BASE_URL = os.getenv("HELIUS_BASE_URL", "https://mainnet.helius-rpc.com")  # Default if not set

# ✅ Birdeye API
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
BIRDEYE_BASE_URL = os.getenv("BIRDEYE_BASE_URL", "https://public-api.birdeye.so")

# ✅ SHYFT API
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
SHYFT_BASE_URL = os.getenv("SHYFT_BASE_URL", "https://api.shyft.to")

# ✅ Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ✅ ML model file path
MODEL_PATH = os.getenv("MODEL_PATH", "revival_predictor.pkl")

# ✅ Initial filters thresholds (example values)
INITIAL_FILTERS = {
    "min_liquidity": 2000,
    "max_deployer_tokens": 20,
    "min_age_minutes": 3,
    "max_market_cap": 100000,
    "min_volume_5m": 200
}
