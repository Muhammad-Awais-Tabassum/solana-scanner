import asyncio import aiohttp import time import logging import uuid from config import INITIAL_FILTERS, BITQUERY_WINDOW_MINUTES, BITQUERY_LIMIT, DEFAULT_SUPPLY, MAX_CONCURRENT_ENRICH from utils.bitquery_api import call_bitquery_api_with_retries from utils.query_templates import build_new_pumpfun_tokens_query from functools import lru_cache

logger = logging.getLogger(name) logger.setLevel(logging.INFO)

seen_mints = set()

@lru_cache(maxsize=2048) def get_cached_metadata_key(mint): return mint

async def extract_mint_address(accounts): for acc in accounts: if acc.get("IsWritable") and not acc.get("IsSigner"): return acc.get("Address") return accounts[0].get("Address") if accounts else None

def clean_string(val): try: return str(val).replace("\x00", "").strip() except: return ""

async def enrich_token_metadata(token, session): mint = token["mint"] if mint in seen_mints: return token

url = f"https://shyft.to/sol/v1/token/info?network=mainnet-beta&token={mint}"
headers = {"accept": "application/json"}

for attempt in range(3):
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                info = data.get("result", {})
                token.update({
                    "marketCap": info.get("market_cap", 0),
                    "holderCount": info.get("holders", 0),
                    "volume24h": info.get("volume_24h", 0),
                    "devHoldingPercent": info.get("ownership", {}).get("owner_percent", 0),
                    "supply": info.get("circulating_supply", DEFAULT_SUPPLY)
                })
                seen_mints.add(mint)
                return token
            elif resp.status in (429, 500, 502, 503):
                await asyncio.sleep(0.5 * (attempt + 1))
    except Exception as e:
        logger.warning(f"[WARN] SHYFT call failed for {mint} on attempt {attempt+1}: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))

logger.warning(f"[WARN] Metadata enrichment failed for {mint}, using fallback")
seen_mints.add(mint)
return token

async def enrich_tokens_with_rate_limit(tokens): semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENRICH)

async with aiohttp.ClientSession() as session:
    async def limited_enrich(token):
        async with semaphore:
            await asyncio.sleep(0.05)  # tune as needed
            return await enrich_token_metadata(token, session)

    return await asyncio.gather(*[limited_enrich(t) for t in tokens])

async def fetch_new_tokens(): start_time = time.time() request_id = str(uuid.uuid4())

logger.info(f"[{request_id}] 🔍 Fetching new tokens via Bitquery...")

try:
    query = build_new_pumpfun_tokens_query(BITQUERY_WINDOW_MINUTES, BITQUERY_LIMIT)
    result = await call_bitquery_api_with_retries(query)

    instructions = result.get("data", {}).get("Solana", {}).get("Instructions", [])
    logger.info(f"[{request_id}] ✅ Found {len(instructions)} instructions")

    new_tokens = []
    for instruction in instructions:
        try:
            accounts = instruction.get("Instruction", {}).get("Accounts", [])
            mint_address = await extract_mint_address(accounts)
            if not mint_address:
                continue

            args = instruction.get("Instruction", {}).get("Program", {}).get("Arguments", [])
            name = symbol = ""

            for arg in args:
                if arg.get("Name") == "name":
                    val = arg.get("Value", {}).get("string") or arg.get("Value", {}).get("json")
                    name = clean_string(val)
                elif arg.get("Name") == "symbol":
                    val = arg.get("Value", {}).get("string") or arg.get("Value", {}).get("json")
                    symbol = clean_string(val)

            new_tokens.append({
                "mint": mint_address,
                "name": name or "Unnamed",
                "symbol": symbol,
                "created_at": instruction.get("Block", {}).get("Time"),
                "deployer": instruction.get("Transaction", {}).get("Signer"),
                "supply": DEFAULT_SUPPLY,
                "marketCap": 0,
                "holderCount": 0,
                "volume24h": 0,
                "devHoldingPercent": 0,
                "buyCount24h": 0,
                "socials": [],
            })
        except Exception as e:
            logger.warning(f"[{request_id}] ⚠️ Failed to parse instruction: {e}")

    logger.info(f"[{request_id}] 📊 Success rate: {len(new_tokens)}/{len(instructions)} tokens parsed")
    enriched_tokens = await enrich_tokens_with_rate_limit(new_tokens)

    enriched_valid = [t for t in enriched_tokens if t.get("marketCap", 0) > 0]
    logger.info(f"[{request_id}] 🎯 Enrichment rate: {len(enriched_valid)}/{len(new_tokens)} tokens enriched")
    logger.info(f"[{request_id}] ⏱️ Completed in {time.time() - start_time:.2f}s")

    return enriched_tokens
except Exception as e:
    logger.error(f"[{request_id}] ❌ Bitquery fetch failed: {e}")
    return []

def apply_filters(token): try: market_cap = token.get("marketCap", 0) holders = token.get("holderCount", 0) volume = token.get("volume24h", 0) dev_percent = token.get("devHoldingPercent", 100) buys = token.get("buyCount24h", 0) socials = token.get("socials", [])

if market_cap < INITIAL_FILTERS["min_marketcap"]:
        return False
    if holders < INITIAL_FILTERS["min_holders"]:
        return False
    if volume < INITIAL_FILTERS["min_volume"]:
        return False
    if dev_percent > INITIAL_FILTERS["max_dev_holding"]:
        return False
    if buys < INITIAL_FILTERS["min_buys"]:
        return False
    if len(socials) < INITIAL_FILTERS["min_socials"]:
        return False

    return True
except Exception as e:
    logger.error(f"[ERROR] Filtering token failed: {e}")
    return False

async def check_new_tokens(): tokens = await fetch_new_tokens() filtered = [t for t in tokens if apply_filters(t)] logger.info(f"[INFO] ✅ {len(filtered)} tokens passed initial filters") return filtered

