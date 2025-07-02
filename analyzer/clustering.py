# analyzer/clustering.py

import aiohttp
import os
from utils.api_helpers import rate_limited_request

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
CLUSTER_URL = f"https://api.helius.xyz/v0/addresses/cluster?api-key={HELIUS_API_KEY}"

async def detect_alt_wallets(deployer_address: str) -> list:
    """
    Fetches wallets that are clustered with the deployer using Helius Enhanced Address Labels API.

    Args:
        deployer_address (str): Wallet address of the token deployer.

    Returns:
        list: A list of wallet addresses in the same cluster.
    """
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "addresses": [deployer_address]
            }
            response = await rate_limited_request(
                session=session,
                method="POST",
                url=CLUSTER_URL,
                json=payload
            )

            cluster_data = await response.json()
            if cluster_data and isinstance(cluster_data, list) and "cluster" in cluster_data[0]:
                return cluster_data[0]["cluster"]
            else:
                return []

    except Exception as e:
        print(f"[CLUSTERING] Error fetching linked wallets: {e}")
        return []
