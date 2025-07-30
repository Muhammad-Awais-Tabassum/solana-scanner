import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 🔑 API Keys
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
HELIUS_BASE_URL = os.getenv("HELIUS_BASE_URL", "https://api.helius.xyz/v0")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY")  # FIXED
BITQUERY_API_URL = "https://streaming.bitquery.io/graphql"
BITQUERY_API_KEY = "ory_at_-e7r82gGAfdBKLDsK9g9-j3Q9IXWQtiaga6zCxskg9s.UvgBu00e9mzedi9eMiWnIACKF7-SCtkjkVDR3fimmyM"
# 📬 Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 🤖 ML Model
MODEL_PATH = os.getenv("MODEL_PATH", "token_revival_model.pkl")

# 📁 Paths
BLACKLIST_PATH = os.getenv("BLACKLIST_PATH", "blacklist.json")

# ⚙️ Thresholds for new tokens
MIN_MARKETCAP_NEW = int(os.getenv("MIN_MARKETCAP_NEW", 7000))
MIN_VOLUME_NEW = int(os.getenv("MIN_VOLUME_NEW", 3000))
MIN_HOLDERS_NEW = int(os.getenv("MIN_HOLDERS_NEW", 5))
MAX_DEV_HOLDING_NEW = float(os.getenv("MAX_DEV_HOLDING_NEW", 15))
MIN_BUYS_NEW = int(os.getenv("MIN_BUYS_NEW", 5))

INITIAL_FILTERS = {
    "min_marketcap": MIN_MARKETCAP_NEW,
    "min_volume": MIN_VOLUME_NEW,
    "min_holders": MIN_HOLDERS_NEW,
    "max_dev_holding": MAX_DEV_HOLDING_NEW,
    "min_buys": MIN_BUYS_NEW,
}

# ⚙️ Graduated token thresholds
MIN_MARKETCAP_GRADUATED = int(os.getenv("MIN_MARKETCAP_GRADUATED", 50000))
MAX_DEV_HOLDING_GRADUATED = float(os.getenv("MAX_DEV_HOLDING_GRADUATED", 5))
MAX_INSIDER_HOLDING = float(os.getenv("MAX_INSIDER_HOLDING", 5))
MIN_VOLUME_GRADUATED = int(os.getenv("MIN_VOLUME_GRADUATED", 500000))
MIN_VOLUME_LAST_5MIN = int(os.getenv("MIN_VOLUME_LAST_5MIN", 100000))
DIP_FROM_ATH_THRESHOLD = float(os.getenv("DIP_FROM_ATH_THRESHOLD", 0.6))

GRADUATED_FILTERS = {
    "min_marketcap": MIN_MARKETCAP_GRADUATED,
    "max_dev_holding": MAX_DEV_HOLDING_GRADUATED,
    "max_insider_holding": MAX_INSIDER_HOLDING,
    "min_volume": MIN_VOLUME_GRADUATED,
    "min_volume_last_5min": MIN_VOLUME_LAST_5MIN,
    "dip_from_ath_threshold": DIP_FROM_ATH_THRESHOLD,
}

# ⚙️ Trending token thresholds
LIQUIDITY_MIN_TRENDING = int(os.getenv("LIQUIDITY_MIN_TRENDING", 8250))
VOLUME_1MIN_MIN_TRENDING = int(os.getenv("VOLUME_1MIN_MIN_TRENDING", 5000))
MC_MIN_TRENDING = int(os.getenv("MC_MIN_TRENDING", 6000))
MC_MAX_TRENDING = int(os.getenv("MC_MAX_TRENDING", 1000000))

TRENDING_FILTERS = {
    "liquidity_min": LIQUIDITY_MIN_TRENDING,
    "volume_5m": VOLUME_1MIN_MIN_TRENDING,  # Reuse same env var for now
    "market_cap_range": (MC_MIN_TRENDING, MC_MAX_TRENDING),
}
