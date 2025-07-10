# filters/graduated_checks.py

import aiohttp
import asyncio
from config import (
    GRADUATED_FILTERS,
    BIRDEYE_API_KEY,
    SHYFT_API_KEY,
)
from utils.bitquery_api import call_bitquery_api

BIRDEYE_TOKEN_INFO = "https://public-api.birdeye.so/public/token/"
SHYFT_METADATA_URL = "https://api.shyft.to/sol/v1/token/get_info?network=mainnet&token="

HEADERS_BIRDEYE = {"X-API-KEY": BIRDEYE_API_KEY}
HEADERS_SHYFT = {"x-api-key": SHYFT_API_KEY}


GRADUATION_QUERY = """
query MyQuery {
  Solana {
    Instructions(
      limit: {count: 50}
      orderBy: {descending: Block_Time}
      where: {
        Instruction: {
          Program: { Address: { is: "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P" } },
          Logs: { includes: { includes: "Migrate" } }
        },
        Transaction: { Result: { Success: true } }
      }
    ) {
      Instruction {
        Accounts {
          Token {
            Mint
          }
        }
      }
    }
  }
}
"""


def extract_mints_from_response(data):
    try:
        instructions = data["data"]["Solana"]["Instructions"]
        mints = []
        for instr in instructions:
            accounts = instr["Instruction"]["Accounts"]
            for acc in accounts:
                token = acc.get("Token")
                if token and token.get("Mint"):
                    mints.append(token["Mint"])
        return list(set(mints))  # remove duplicates
    except Exception as e:
        print(f"[ERROR] Failed to parse Bitquery response: {e}")
        return []


async def get_birdeye_data(session, mint):
    async with session.get(BIRDEYE_TOKEN_INFO + mint, headers=HEADERS_BIRDEYE) as resp:
        if resp.status != 200:
            return {}
        data = await resp.json()
        return data.get("data", {})


async def get_token_metadata(session, mint):
    async with session.get(SHYFT_METADATA_URL + mint, headers=HEADERS_SHYFT) as resp:
        if resp.status != 200:
            return {}
        result = await resp.json()
        return result.get("result", {})


def apply_graduated_filters(birdeye_data, metadata):
    try:
        market_cap = birdeye_data.get("mc", 0)
        volume = birdeye_data.get("volume24h", 0)
        price = birdeye_data.get("price_usd", 0)
        ath = birdeye_data.get("ath", price)

        dev_holdings = metadata.get("token_info", {}).get("creator_token_holdings", 100)
        creators = metadata.get("creators", [])

        if market_cap < GRADUATED_FILTERS["market_cap_min"]:
            return False
        if volume < GRADUATED_FILTERS["volume_min"]:
            return False
        if ath != 0:
            dip = ((ath - price) / ath) * 100
            if dip < GRADUATED_FILTERS["price_dip_pct"]:
                return False
        if dev_holdings > GRADUATED_FILTERS["dev_max_percent"]:
            return False
        if creators and len(creators) > 1:
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Filter logic failed: {e}")
        return False


async def analyze_token(session, mint):
    try:
        birdeye_data = await get_birdeye_data(session, mint)
        metadata = await get_token_metadata(session, mint)

        if not apply_graduated_filters(birdeye_data, metadata):
            return None

        return {
            "mint": mint,
            "name": birdeye_data.get("name", "Unnamed"),
            "price": birdeye_data.get("price_usd"),
            "volume": birdeye_data.get("volume24h"),
            "market_cap": birdeye_data.get("mc"),
        }
    except Exception as e:
        print(f"[ERROR] Token {mint} failed: {e}")
        return None


async def check_graduated_tokens():
    print("🔍 Querying Bitquery for graduated tokens...")
    response = call_bitquery_api(GRADUATION_QUERY)
    if not response:
        return []

    mints = extract_mints_from_response(response)
    print(f"[INFO] {len(mints)} potential graduated tokens found.")

    async with aiohttp.ClientSession() as session:
        tasks = [analyze_token(session, mint) for mint in mints]
        results = await asyncio.gather(*tasks)
        graduated = [r for r in results if r]
        print(f"[INFO] {len(graduated)} graduated tokens passed all filters.")
        return graduated


# Optional local test
if __name__ == "__main__":
    asyncio.run(check_graduated_tokens())
