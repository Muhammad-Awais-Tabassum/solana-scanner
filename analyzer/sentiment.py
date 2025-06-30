import tweepy
import os
from datetime import datetime, timedelta
from config import TWITTER_BEARER_TOKEN

client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)


async def search_tweets(contract_address, max_results=100):
    query = f"{contract_address} lang:en -is:retweet"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=max_results, tweet_fields=["created_at", "author_id"])
        return tweets.data if tweets.data else []
    except Exception as e:
        print(f"[ERROR] Twitter search failed: {e}")
        return []


async def get_user_profile(user_id):
    try:
        user = client.get_user(id=user_id, user_fields=["username", "name", "description", "verified", "public_metrics"])
        return user.data
    except Exception as e:
        print(f"[ERROR] Could not fetch user profile: {e}")
        return None


async def summarize_sentiment(tweets):
    bullish = 0
    bearish = 0
    neutral = 0

    keywords = {
        "bullish": ["buying", "moon", "sending", "up only", "pump"],
        "bearish": ["rug", "scam", "dump", "exit", "avoid"],
    }

    for tweet in tweets:
        text = tweet.text.lower()
        if any(k in text for k in keywords["bullish"]):
            bullish += 1
        elif any(k in text for k in keywords["bearish"]):
            bearish += 1
        else:
            neutral += 1

    total = bullish + bearish + neutral
    if total == 0:
        return "neutral"
    ratio = bullish / total
    if ratio > 0.6:
        return "bullish"
    elif bearish / total > 0.5:
        return "bearish"
    else:
        return "neutral"


async def analyze_twitter(contract_address):
    tweets = await search_tweets(contract_address)
    sentiment = await summarize_sentiment(tweets)

    notable_mentions = []
    seen_accounts = set()

    for tweet in tweets:
        if tweet.author_id in seen_accounts:
            continue

        profile = await get_user_profile(tweet.author_id)
        if not profile:
            continue

        followers = profile.public_metrics["followers_count"]
        if profile.verified or followers > 10000:
            notable_mentions.append({
                "username": profile.username,
                "followers": followers,
                "verified": profile.verified
            })
        seen_accounts.add(tweet.author_id)

    print(f"[INFO] Sentiment: {sentiment}, Notables: {len(notable_mentions)}")
    return {
        "sentiment": sentiment,
        "notables": notable_mentions,
        "tweet_count": len(tweets)
    }


# Example usage
if __name__ == "__main__":
    import asyncio
    contract = "EXAMPLE_CONTRACT_ADDRESS"
    result = asyncio.run(analyze_twitter(contract))
    print(result)
