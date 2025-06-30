# notifier/telegram.py

import aiohttp
import asyncio
import base64
import logging
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Channel or user ID

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


async def send_message(text: str, parse_mode="Markdown"):
    """
    Sends a plain text message to the Telegram channel.
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                logging.warning(f"Telegram message failed: {resp.status}")
            return await resp.json()


async def send_photo_from_base64(image_base64: str, caption: str = ""):
    """
    Sends a base64 image (like price chart) to the Telegram channel.
    """
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    photo_bytes = base64.b64decode(image_base64)

    data = aiohttp.FormData()
    data.add_field('chat_id', TELEGRAM_CHAT_ID)
    data.add_field('photo', photo_bytes, filename='plot.png', content_type='image/png')
    data.add_field('caption', caption)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            if resp.status != 200:
                logging.warning(f"Telegram photo failed: {resp.status}")
            return await resp.json()


# Example usage (when testing standalone)
if __name__ == "__main__":
    asyncio.run(send_message("🚀 Test message from Solana Meme Scanner!"))