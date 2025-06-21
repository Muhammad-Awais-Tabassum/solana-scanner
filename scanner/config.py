import os
from dotenv import load_dotenv
load_dotenv()

TEL = os.getenv("TELEGRAM_TOKEN").strip()
CHAT = os.getenv("TELEGRAM_CHAT_ID").strip()
BITQ = os.getenv("BITQUERY_API_KEY").strip()
HELIUS = os.getenv("HELIUS_API_KEY").strip()
TWITTER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN").strip()