import asyncio 
import aiohttp 
import logging 
import time from config 
import INITIAL_FILTERS, BITQUERY_LOOKBACK_MINUTES, BITQUERY_LIMIT, DEFAULT_SUPPLY, MAX_CONCURRENT_ENRICH from utils.bitquery_api 
import call_bitquery_api_with_retries from utils.helpers 
import generate_request_id from datetime import datetime, timedelta from functools import lru_cache from typing 
import List, Dict, Any

logger = logging.getLogger(name)

Global seen_mints set to prevent re-fetching

seen_mints = set()

Circuit breaker state

circuit_breaker_open = False circuit_breaker_reset_time = None CIRCUIT_BREAKER_TIMEOUT = 300  # seconds CIRCUIT_BREAKER_THRESHOLD = 5 circuit_failure_count = 0

BIRDEYE_URL = "https://public-api.birdeye.so/defi/v3/token/meta-data/single" BIRDEYE_HEADERS = { "accept": "application/json", "x-chain": "solana" }

def build_bitquery_query(since_iso: str, limit: int) -> str: return f""" query NewPumpFunTokens {{ Solana(network: solana) {{ Instructions( limit: {{count: {limit}}} orderBy: {{descending: Block_Time}} where: {{ Instruction: {{ Program: {{ Name: {{is: "pump"}} Method: {{is: "create"}} }} }} Block: {{ Time: {{since: "{since_iso}"}} }} }} ) {{ Block {{ Time }} Transaction {{ Signer Signature }} Instruction {{ Accounts {{ Address IsWritable IsSigner }} Program {{ Arguments {{ Name Value {{ ... on Solana_ABI_Json_Value_Arg {{ json }} ... on Solana_ABI_String_Value_Arg {{ string }} }} }} }} }} }} }} }} """

def extract_mint_address(accounts): for account in accounts: addr = account.get("Address") if addr and account.get("IsWritable", False) and not account.get("IsSigner", False): return addr return accounts[0].get("Address") if accounts else None

def clean_string(value): if isinstance(value, str): return value.strip() elif isinstance(value, dict): return str(value) return ""

async def enrich_token_metadata(session, token): global circuit_breaker_open, circuit_breaker_reset_time, circuit_failure_count

mint = token["mint"]
if mint in seen_mints:
    return token

if circuit_breaker_open and time.time() < circuit_breaker_reset_time:
    logger.warning("🚫 Circuit breaker active, skipping enrichment for %s", mint)
    return token

retries = 3
for attempt in range(retries):
    try:
        async with session.get(
            f"{BIRDEYE_URL}?address={mint}",
            headers=BIRDEYE_HEADERS,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                token["marketCap"] = data.get("market_cap", 0)
                token["volume24h"] = data.get("volume_24h", 0)
                token["holderCount"] = data.get("holders", 0)
                token["supply"] = data.get("supply", DEFAULT_SUPPLY)
                token["symbol"] = data.get("symbol") or token["symbol"]
                token["name"] = data.get("name") or token["name"]
                seen_mints.add(mint)
                circuit_failure_count = 0
                return token
            else:
                logger.warning(f"[WARN] Birdeye failed for {mint}: HTTP {resp.status}")

    except Exception as e:
        logger.warning(f"[WARN] Error enriching {mint}: {e}")
        await asyncio.sleep(2 ** attempt)

circuit_failure_count += 1
if circuit_failure_count >= CIRCUIT_BREAKER_THRESHOLD:
    circuit_breaker_open = True
    circuit_breaker_reset_time = time.time() + CIRCUIT_BREAKER_TIMEOUT
    logger.error("🚨 Circuit breaker triggered: too many Birdeye failures")

return token

async def enrich_tokens_with_rate_limit(tokens, max_concurrent=MAX_CONCURRENT_ENRICH): semaphore = asyncio.Semaphore(max_concurrent)

async with aiohttp.ClientSession() as session:
    async def limited_enrich(token):
        async with semaphore:
            await asyncio.sleep(0.1)
            return await enrich_token_metadata(session, token)

    return await asyncio.gather(*[limited_enrich(t) for t in tokens])

async def fetch_new_tokens(): start_time = time.time() request_id = generate_request_id() since_time = datetime.utcnow() - timedelta(minutes=BITQUERY_LOOKBACK_MINUTES) query = build_bitquery_query(since_time.isoformat(), BITQUERY_LIMIT)

logger.info(f"🔍 [{request_id}] Querying Bitquery for new Pump.Fun tokens...")
result = await call_bitquery_api_with_retries(query)

if not result or "data" not in result or "Solana" not in result["data"]:
    logger.error(f"[ERROR] Bitquery response invalid or empty for req {request_id}")
    return []

instructions = result["data"]["Solana"].get("Instructions", [])
logger.info(f"✅ [{request_id}] Found {len(instructions)} token instructions")

new_tokens = []
for instruction in instructions:
    try:
        accounts = instruction["Instruction"].get("Accounts", [])
        mint = extract_mint_address(accounts)
        if not mint:
            continue

        args = instruction["Instruction"].get("Program", {}).get("Arguments", [])
        name, symbol = "Unnamed", ""
        for arg in args:
            val = arg.get("Value", {})
            if arg["Name"] == "name":
                name = clean_string(val.get("string") or val.get("json"))
            elif arg["Name"] == "symbol":
                symbol = clean_string(val.get("string") or val.get("json"))

        new_tokens.append({
            "mint": mint,
            "name": name,
            "symbol": symbol,
            "created_at": instruction["Block"].get("Time"),
            "deployer": instruction["Transaction"].get("Signer"),
            "supply": DEFAULT_SUPPLY,
            "marketCap": 0,
            "holderCount": 0,
            "volume24h": 0,
            "devHoldingPercent": 0,
            "buyCount24h": 0,
            "socials": [],
        })

    except Exception as e:
        logger.warning(f"[WARN] Parse failure: {e}")

logger.info(f"📊 [{request_id}] Parsed {len(new_tokens)} tokens")
enriched_tokens = await enrich_tokens_with_rate_limit(new_tokens)
logger.info(f"🎯 [{request_id}] Enriched {len([t for t in enriched_tokens if t['marketCap'] > 0])}/{len(enriched_tokens)} tokens")
logger.info(f"⏱️ [{request_id}] Done in {time.time() - start_time:.2f}s")

return enriched_tokens

def apply_filters(token): try: return ( token.get("marketCap", 0) >= INITIAL_FILTERS["min_marketcap"] and token.get("holderCount", 0) >= INITIAL_FILTERS["min_holders"] and token.get("volume24h", 0) >= INITIAL_FILTERS["min_volume"] and token.get("devHoldingPercent", 100) <= INITIAL_FILTERS["max_dev_holding"] and token.get("buyCount24h", 0) >= INITIAL_FILTERS["min_buys"] and len(token.get("socials", [])) >= INITIAL_FILTERS["min_socials"] ) except Exception as e: logger.error(f"[ERROR] Filtering token failed: {e}") return False

async def check_new_tokens(): raw_tokens = await fetch_new_tokens() filtered = [t for t in raw_tokens if apply_filters(t)] logger.info(f"✅ Final Filtered Tokens: {len(filtered)}") return filtered

