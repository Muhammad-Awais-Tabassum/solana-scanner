import aiohttp
import asyncio

SHYFT_API_KEY = "your_shyft_api_key_here"
SHYFT_WALLET_LOOKUP = "https://api.shyft.to/sol/v1/wallet/all_tokens?network=mainnet-beta&wallet={wallet}"

async def fetch_wallet_tokens(wallet):
    url = SHYFT_WALLET_LOOKUP.format(wallet=wallet)
    headers = {"x-api-key": SHYFT_API_KEY}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("result", [])
                else:
                    print(f"[ERROR] SHYFT lookup failed: {resp.status}")
        except Exception as e:
            print(f"[ERROR] Wallet inspection failed: {e}")
    return []

def analyze_wallet_holdings(tokens):
    spl_count = len([t for t in tokens if t.get("type") == "spl"])
    nft_count = len([t for t in tokens if t.get("type") == "nft"])
    suspicious = any(t.get("amount", 0) > 1e9 for t in tokens)  # Detect abnormal holdings

    return {
        "spl_count": spl_count,
        "nft_count": nft_count,
        "suspicious": suspicious
    }


# Example usage
if __name__ == "__main__":
    async def main():
        wallet = "3PNf5p7cttG..."
        tokens = await fetch_wallet_tokens(wallet)
        result = analyze_wallet_holdings(tokens)
        print(result)

    asyncio.run(main())
