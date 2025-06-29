import os
from dotenv import load_dotenv

def load_config():
    load_dotenv()
    return {
        "helius_api_key": os.getenv("HELIUS_API_KEY"),
        "birdeye_api_key": os.getenv("BIRDEYE_API_KEY"),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "blacklisted_deployers": os.getenv("BLACKLISTED_DEPLOYERS", "").split(",")
    }