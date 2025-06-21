import requests
from scanner.config import TEL, CHAT

def tg(msg):
    requests.post(
        f"https://api.telegram.org/bot{TEL}/sendMessage",
        data={'chat_id': CHAT, 'text': msg, 'parse_mode': 'HTML'}
    )