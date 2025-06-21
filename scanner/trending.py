import time
import requests
from scanner.monitor import analyze
from playwright.sync_api import sync_playwright
import os

BITQ = os.getenv("BITQUERY_API_KEY")
seen_trending = set()

# === Trending Token from pump.fun frontend ===
def fetch_trending_visual():
    trending = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://pump.fun", timeout=60000)
        time.sleep(5)

        try:
            links = page.locator("a[href*='/token/']").all()
            for link in links[:15]:
                href = link.get_attribute("href")
                if href and "/token/" in href:
                    mint = href.split("/token/")[-1].strip()
                    name = link.inner_text().strip()[:12] or "Trend"
                    trending.append({'name': name, 'address': mint, 'deployer': mint[-10:]})
        except Exception as e:
            print("🔥 Error parsing frontend trending:", e)

        browser.close()
    return trending

# === Trending tokens by real volume from Bitquery ===
def fetch_trending_bitquery():
    query = {
        "query": """
        {
          solana {
            dexTrades(
              options: {limit: 10, desc: "tradeAmount"},
              date: {since: "-1h"}
            ) {
              baseCurrency {
                address
              }
              tradeAmount
              count
            }
          }
        }
        """
    }
    try:
        res = requests.post(
            "https://graphql.bitquery.io/",
            json=query,
            headers={"X-API-KEY": BITQ}
        )
        trades = res.json().get("data", {}).get("solana", {}).get("dexTrades", [])
        result = []
        for t in trades:
            mint = t["baseCurrency"]["address"]
            if mint:
                result.append({"name": "Trending", "address": mint, "deployer": mint[-10:]})
        return result
    except Exception as e:
        print("Bitquery trending error:", e)
        return []

# === Main trending loop ===
def trending_monitor():
    print("🔥 Trending monitor started...")
    while True:
        visual = fetch_trending_visual()
        for token in visual:
            if token['address'] not in seen_trending:
                print("🔥 Visual Trending:", token['name'])
                analyze(token, trending=True)
                seen_trending.add(token['address'])

        onchain = fetch_trending_bitquery()
        for token in onchain:
            if token['address'] not in seen_trending:
                print("📊 On-chain Trending:", token['name'])
                analyze(token, trending=True)
                seen_trending.add(token['address'])

        time.sleep(300)
