import aiohttp
from aiolimiter import AsyncLimiter
from async_retrying import retry
import backoff
import logging

class BaseAPIClient:
    def __init__(self, api_key: str, base_url: str, rate_limit: int = 100):
        self.api_key = api_key
        self.base_url = base_url
        self.limiter = AsyncLimiter(rate_limit, 60)  # 100 calls/minute
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def close(self):
        await self.session.close()

    @retry(attempts=3, delay=1)
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _get(self, endpoint: str, params: dict = None):
        async with self.limiter:
            url = f"{self.base_url}/{endpoint}"
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 429:
                        logging.warning(f"Rate limit hit on {url}")
                        await asyncio.sleep(5)
                    response.raise_for_status()
            except Exception as e:
                logging.error(f"API request failed to {url}: {str(e)}")
                raise

    @retry(attempts=3, delay=1)
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _post(self, endpoint: str, payload: dict):
        async with self.limiter:
            url = f"{self.base_url}/{endpoint}"
            try:
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 429:
                        logging.warning(f"Rate limit hit on {url}")
                        await asyncio.sleep(5)
                    response.raise_for_status()
            except Exception as e:
                logging.error(f"API request failed to {url}: {str(e)}")
                raise

class HeliusClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://mainnet.helius-rpc.com")

    async def get_recent_mints(self, limit: int = 100):
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "getRecentTokenMints",
            "params": {"limit": limit}
        }
        return await self._post(f"?api-key={self.api_key}", payload)

    async def get_token_metadata(self, mint_address: str):
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "getAsset",
            "params": {"id": mint_address}
        }
        return await self._post(f"?api-key={self.api_key}", payload)

class BirdeyeClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://public-api.birdeye.so/public")
        self.headers = {"X-API-KEY": self.api_key}

    async def get_trending_tokens(self):
        return await self._get("trending", params={"sort_by": "volume"})

    async def get_token_price(self, mint_address: str):
        return await self._get(f"price?address={mint_address}")

class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = aiohttp.ClientSession()

    async def send_alert(self, message: str):
        url = f"{self.base_url}/sendMessage"
        params = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        async with self.session.post(url, json=params) as response:
            return await response.json()