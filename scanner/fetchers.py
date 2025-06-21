import requests
from bs4 import BeautifulSoup
from scanner.config import BITQ, HELIUS, TWITTER_TOKEN
from playwright.sync_api import sync_playwright
import time

def fetch_bitquery(mint):
    query = {
        'query': f'''{{
          solana {{
            token(mintAddress: "{mint}") {{ marketCap }}
            tokenHolders(limit:10, tokenAddress:"{mint}"){{amount}}
          }}
        }}'''
    }
    r = requests.post("https://graphql.bitquery.io/", json=query, headers={'X-API-KEY': BITQ}).json()
    sol = r.get("data", {}).get("solana", {})
    mc = float(sol.get("token", [{}])[0].get("marketCap") or 0)
    holders_amt = sum(float(h['amount']) for h in sol.get("tokenHolders", []))
    return mc, holders_amt

def fetch_deployer_hist(w):
    return requests.get(
        f"https://api.helius.xyz/v0/addresses/{w}/transactions?api-key={HELIUS}"
    ).json()

def fetch_twitter_sentiment(mint):
    url = f"https://api.twitter.com/2/tweets/search/recent?query={mint}&tweet.fields=public_metrics"
    h = {"Authorization": f"Bearer {TWITTER_TOKEN}"}
    r = requests.get(url, headers=h).json().get("data", [])
    positivity = sum(t['public_metrics']['retweet_count'] + t['public_metrics']['like_count']
                    for t in r)
    return len(r), positivity

def fetch_pumpfun():
    out=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        pg=b.new_page(); pg.goto("https://pump.fun", timeout=60000)
        time.sleep(5)
        for a in BeautifulSoup(pg.content(),"html.parser").select("a[href*='/token/']"):
            m=a['href'].split("/")[-1]
            out.append({'name':a.text.strip()[:10],'address':m,'deployer':m[-10:]})
        b.close()
    return out
