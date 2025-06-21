import os, time, sys
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from scanner.fetchers import fetch_pumpfun, fetch_bitquery, fetch_deployer_hist, fetch_twitter_sentiment
from scanner.analysis import calc_confidence
from scanner.alerts import tg

blacklist = {}; MAX_FAIL=3

def setup_sheet():
    creds_json = os.getenv("GOOGLE_CREDS_B64")
    import json, base64
    creds_dict = json.loads(base64.b64decode(creds_json))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        creds_dict,
        ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds).open("PumpFun Scanner Log").sheet1

sheet = setup_sheet()

def analyze(t):
    mint, dep = t['address'], t['deployer']
    if blacklist.get(dep,0) >= MAX_FAIL: return

    mc, top_amt = fetch_bitquery(mint)
    if mc < 30000: blacklist[dep] = blacklist.get(dep, 0) + 1; return

    hist = fetch_deployer_hist(dep)
    created = [tx for tx in hist if tx.get("type") == "TOKEN_MINT"]
    bad = [x for x in created if float(x.get("marketCap", 0)) < 200_000]
    if created and len(bad) / len(created) >= 0.97: blacklist[dep] = MAX_FAIL; return

    ds = 1 if created else 0
    sn, ins, top_holders_pct = 0, 0, (100 * top_amt / (mc or 1))
    if top_holders_pct > 25: blacklist[dep] += 1; return

    tw_count, tw_pop = fetch_twitter_sentiment(mint)
    conf = calc_confidence(ds, len(created)*50, sn, ins, tw_count)
    prob = min(95, max(10, conf))

    msg = (
        f"🚨 <b>NEW TOKEN PASSED FILTERS!</b>\n"
        f"🪙 <b>Name:</b> ${t['name']}\n"
        f"📈 <b>Market Cap:</b> ${mc:,.0f}\n"
        f"🔍 <b>Confidence:</b> {conf}/100\n"
        f"🎯 <b>Success Prob:</b> {prob}%\n"
        f"💰 <b>Deployer:</b> {'CLEAN' if ds else 'MID'} ({len(created)} prev tokens)\n"
        f"🐦 <b>Twitter Mentions:</b> {tw_count}, Popularity: {tw_pop}\n"
        f"🔗 https://explorer.solana.com/address/{mint}"
    )
    tg(msg)
    sheet.append_row([
        datetime.utcnow().isoformat(),
        t['name'], mc, len(created)*50, conf, prob,
        ('CLEAN' if ds else 'MID'), len(created),
        tw_count, tw_pop, mint
    ])

def monitor():
    print("✅ Monitor started", flush=True)
    seen = set()
    while True:
        print("🔁 Checking for new tokens...", flush=True)
        for tok in fetch_pumpfun():
            if tok['address'] not in seen:
                analyze(tok); seen.add(tok['address'])
        time.sleep(60)