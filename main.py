import asyncio
from scanner import (
    pumpfun_scanner,
    deployer_check,
    holder_analysis,
    twitter_sentiment,
    confidence_score,
    telegram_notifier,
    blacklist,
    wallet_inspector,
    async_executor,
    birdeye_scanner,
    shyft_inspector,
)
from config import TELEGRAM_CHAT_ID

async def process_token(token):
    contract = token.get("contract")
    if not contract:
        return

    # Skip if already blacklisted
    if blacklist.is_blacklisted(token["deployer"]):
        return

    # Run core checks
    deployer_ok = await deployer_check.check_deployer_history(token["deployer"])
    if not deployer_ok:
        blacklist.add_to_blacklist(token["deployer"])
        return

    holders_ok = await holder_analysis.analyze_holders(contract)
    if not holders_ok:
        blacklist.add_to_blacklist(token["deployer"])
        return

    sentiment = await twitter_sentiment.search_token_mentions(contract)
    shyft_data = await shyft_inspector.get_wallet_data(token["deployer"])
    confidence = confidence_score.compute(token, sentiment, shyft_data)

    if confidence >= 0.75:
        summary = f"""
🚀 *New Meme Coin Opportunity* 🚀
Contract: `{contract}`
Confidence: *{confidence:.2f}*
Deployer: `{token['deployer']}`
Socials: {token.get("socials", ['N/A'])}
Volume: {token.get('volume', 0)}
Market Cap: {token.get('market_cap', 0)}
Holders: {token.get('holders', 0)}
Mentioned in {sentiment['mention_count']} tweets.

#Solana #MemeCoin
        """.strip()
        await telegram_notifier.send_message(TELEGRAM_CHAT_ID, summary)

async def main():
    print("🔍 Scanning Pump.fun tokens...")
    pumpfun_tokens = await pumpfun_scanner.fetch_new_tokens()
    await async_executor.run_concurrently([process_token(t) for t in pumpfun_tokens])

    print("🔥 Scanning trending tokens (Birdeye)...")
    trending = await birdeye_scanner.get_trending_tokens()
    await async_executor.run_concurrently([process_token(t) for t in trending])

if __name__ == "__main__":
    asyncio.run(main())
