# main.py

import asyncio
from filters.initial_checks import check_new_tokens
from filters.graduated_checks import check_graduated_tokens
from filters.trending_checks import fetch_trending_tokens
from filters.extra_heuristics import apply_extra_heuristics

from analyzer.deployer_history import check_deployer_history
from analyzer.wallet_analysis import analyze_wallets
from analyzer.sentiment import analyze_sentiment
from analyzer.clustering import detect_alt_wallets


from notifier.telegram import send_telegram_alert
from utils.api_helpers import get_token_metadata
from utils.visualizer import plot_price_vs_time
from config import GRADUATED_FILTERS, TRENDING_FILTERS


async def process_token(token):
    # Fetch metadata and basic token info
    metadata = await get_token_metadata(token["mint"])
    if not metadata:
        return

    # Deployer check
    deployer_passed, deployer_data = await check_deployer_history(token["deployer"])
    if not deployer_passed:
        return

    # Wallet clustering
    alt_wallets = await detect_alt_wallets(token["deployer"])

    # Wallet & holder analysis
    holder_passed, holder_details = await analyze_wallets(token["mint"], token["deployer"])
    if not holder_passed:
        return

    # Sentiment analysis
    sentiment = await analyze_sentiment(token["mint"])

    # Heuristics filtering
    if not apply_extra_heuristics(token["mint"]):
        return

    

    # Visualization
    chart_path = await plot_price_vs_time(token["mint"])

    # Format and send to Telegram
    summary = {
        "token": token,
        "metadata": metadata,
        "deployer": deployer_data,
        "holders": holder_details,
        "alt_wallets": alt_wallets,
        "sentiment": sentiment,
        "revival_prediction": is_recovering,
        "probability": probability
    }

    await send_telegram_alert(summary, chart_path)


async def main():
    print("📈 Scanning PumpFun New Tokens...")
    tokens = await check_new_tokens()

    if GRADUATED_FILTERS:
        print("🎓 Scanning Graduated Tokens...")
        graduated_tokens = await check_graduated_tokens()
    for token in graduated_tokens:
        token["source"] = "graduated"
    tokens += graduated_tokens

    if TRENDING_FILTERS:
        print("🔥 Scanning Trending Tokens...")
        tokens += await fetch_trending_tokens()

    print(f"✅ {len(tokens)} tokens passed basic filters.")

    tasks = [process_token(token) for token in tokens]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
