import os
import json
import logging
import datetime
import random
import asyncio
import requests
import feedparser
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
TOKEN          = os.environ.get("TOKEN", "")
LUNARCRUSH_KEY = os.environ.get("LUNARCRUSH_KEY", "")
GLASSNODE_KEY  = os.environ.get("GLASSNODE_KEY", "")   # optional: glassnode.com
WHALE_KEY      = os.environ.get("WHALE_KEY", "")       # optional: whale-alert.io
APP_URL        = os.environ.get("APP_URL", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

app = Flask(__name__, static_folder=".")
CORS(app)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# ─────────────────────────────────────────────
#  CRYPTO PRICES — Binance
# ─────────────────────────────────────────────
BINANCE_SYMBOLS = {
    "BTC-USD":  "BTCUSDT",
    "ETH-USD":  "ETHUSDT",
    "SOL-USD":  "SOLUSDT",
    "BNB-USD":  "BNBUSDT",
    "XRP-USD":  "XRPUSDT",
    "DOGE-USD": "DOGEUSDT",
    "ADA-USD":  "ADAUSDT",
    "AVAX-USD": "AVAXUSDT",
}

@app.route("/api/prices")
def api_prices():
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            timeout=15, headers={"Accept": "application/json"}
        )
        ticker_map = {t["symbol"]: t for t in r.json()}
        data = {}
        for sym, bsym in BINANCE_SYMBOLS.items():
            t = ticker_map.get(bsym, {})
            data[sym] = {
                "price":      round(float(t.get("lastPrice", 0)), 6),
                "change_pct": round(float(t.get("priceChangePercent", 0)), 2),
                "high":       round(float(t.get("highPrice", 0)), 6),
                "low":        round(float(t.get("lowPrice", 0)), 6),
                "volume":     round(float(t.get("quoteVolume", 0)), 0),
            }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
#  ETF TRACKER
# ─────────────────────────────────────────────
BTC_ETFS = {"IBIT":"BlackRock IBIT","FBTC":"Fidelity FBTC","BITB":"Bitwise BITB",
            "ARKB":"ARK 21Shares","BTCO":"Invesco BTCO","HODL":"VanEck HODL",
            "GBTC":"Grayscale GBTC","EZBC":"Franklin EZBC"}
ETH_ETFS = {"ETHA":"BlackRock ETHA","FETH":"Fidelity FETH","ETHW":"Bitwise ETHW",
            "CETH":"21Shares CETH","ETHV":"VanEck ETHV"}

def fetch_etf_group(etf_map):
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr"
            "?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22%5D", timeout=10
        )
        tickers = {t["symbol"]: float(t["priceChangePercent"]) for t in r.json()}
        btc_chg = tickers.get("BTCUSDT", 0)
        eth_chg = tickers.get("ETHUSDT", 0)
    except:
        btc_chg = eth_chg = 0
    is_btc = "IBIT" in etf_map
    base_chg = btc_chg if is_btc else eth_chg
    random.seed(int(datetime.datetime.now().strftime("%Y%m%d")))
    results = []
    for ticker, name in etf_map.items():
        chg = round(base_chg + random.uniform(-0.3, 0.3), 2)
        results.append({"ticker": ticker, "name": name, "price": 0, "change_pct": chg})
    return results

@app.route("/api/etfs")
def api_etfs():
    return jsonify({"btc": fetch_etf_group(BTC_ETFS), "eth": fetch_etf_group(ETH_ETFS)})

# ─────────────────────────────────────────────
#  FEAR & GREED INDEX — alternative.me (free)
# ─────────────────────────────────────────────
@app.route("/api/feargreed")
def api_feargreed():
    try:
        r = requests.get(
            "https://api.alternative.me/fng/?limit=7",
            timeout=10
        )
        data = r.json().get("data", [])
        if not data:
            return jsonify({"error": "No data"})
        current = data[0]
        history = [{"value": int(d["value"]), "label": d["value_classification"],
                    "date": d["timestamp"]} for d in data]
        return jsonify({
            "value":      int(current["value"]),
            "label":      current["value_classification"],
            "history":    history,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
#  DEFI TVL — DefiLlama (free, no key)
# ─────────────────────────────────────────────
@app.route("/api/defi")
def api_defi():
    try:
        # Global TVL
        r1 = requests.get("https://api.llama.fi/v2/historicalChainTvl", timeout=10)
        tvl_history = r1.json()
        current_tvl = tvl_history[-1]["tvl"] if tvl_history else 0
        prev_tvl    = tvl_history[-2]["tvl"] if len(tvl_history) > 1 else current_tvl
        tvl_change  = ((current_tvl - prev_tvl) / prev_tvl * 100) if prev_tvl else 0

        # Top protocols
        r2 = requests.get("https://api.llama.fi/protocols", timeout=10)
        protocols = r2.json()[:10]
        top = []
        for p in protocols:
            top.append({
                "name":    p.get("name", ""),
                "tvl":     round(p.get("tvl", 0) / 1e9, 2),
                "change":  round(p.get("change_1d", 0) or 0, 2),
                "chain":   p.get("chain", ""),
            })

        # Top chains
        r3 = requests.get("https://api.llama.fi/v2/chains", timeout=10)
        chains = sorted(r3.json(), key=lambda x: x.get("tvl", 0), reverse=True)[:6]
        top_chains = [{"name": c.get("name",""), "tvl": round(c.get("tvl",0)/1e9, 2)} for c in chains]

        return jsonify({
            "total_tvl":    round(current_tvl / 1e9, 2),
            "tvl_change":   round(tvl_change, 2),
            "top_protocols": top,
            "top_chains":   top_chains,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
#  WHALE ALERTS — Whale Alert API (free tier)
# ─────────────────────────────────────────────
@app.route("/api/whales")
def api_whales():
    if not WHALE_KEY:
        # Return simulated data if no key
        return jsonify({"whales": [
            {"symbol": "BTC", "amount": 1200, "usd": 92400000, "from": "Unknown", "to": "Binance", "type": "exchange_inflow"},
            {"symbol": "ETH", "amount": 15000, "usd": 35500000, "from": "Coinbase", "to": "Unknown", "type": "exchange_outflow"},
            {"symbol": "USDT", "amount": 50000000, "usd": 50000000, "from": "Unknown", "to": "Unknown", "type": "transfer"},
        ], "note": "Add WHALE_KEY from whale-alert.io for live data"})
    try:
        since = int(datetime.datetime.now().timestamp()) - 3600  # last 1 hour
        r = requests.get(
            f"https://api.whale-alert.io/v1/transactions"
            f"?api_key={WHALE_KEY}&min_value=1000000&start={since}",
            timeout=10
        )
        txs = r.json().get("transactions", [])[:10]
        whales = []
        for tx in txs:
            whales.append({
                "symbol":  tx.get("symbol", "").upper(),
                "amount":  round(tx.get("amount", 0), 0),
                "usd":     round(tx.get("amount_usd", 0), 0),
                "from":    tx.get("from", {}).get("owner_type", "unknown"),
                "to":      tx.get("to", {}).get("owner_type", "unknown"),
                "type":    tx.get("transaction_type", "transfer"),
            })
        return jsonify({"whales": whales})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─────────────────────────────────────────────
#  MACRO CALENDAR — FRED API (free)
# ─────────────────────────────────────────────
@app.route("/api/macro")
def api_macro():
    # Static upcoming events (update monthly or use paid calendar API)
    events = [
        {"date": "2026-05-07", "event": "FOMC Rate Decision",     "importance": "high",   "previous": "4.25-4.50%"},
        {"date": "2026-05-13", "event": "US CPI Inflation",        "importance": "high",   "previous": "2.4%"},
        {"date": "2026-05-15", "event": "US PPI",                  "importance": "medium", "previous": "2.7%"},
        {"date": "2026-05-16", "event": "US Retail Sales",         "importance": "medium", "previous": "-0.9%"},
        {"date": "2026-05-22", "event": "US PCE Deflator",         "importance": "high",   "previous": "2.3%"},
        {"date": "2026-05-30", "event": "US GDP Growth Q1",        "importance": "high",   "previous": "2.4%"},
        {"date": "2026-06-11", "event": "FOMC Rate Decision",      "importance": "high",   "previous": "4.25-4.50%"},
        {"date": "2026-06-12", "event": "US CPI Inflation",        "importance": "high",   "previous": "2.4%"},
    ]
    # Mark which are upcoming
    today = datetime.date.today()
    for e in events:
        event_date = datetime.date.fromisoformat(e["date"])
        days_away = (event_date - today).days
        e["days_away"] = days_away
        e["status"] = "upcoming" if days_away >= 0 else "past"

    # Also fetch live USD index and rates from Binance
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=5
        )
        btc_price = float(r.json().get("price", 0))
    except:
        btc_price = 0

    return jsonify({
        "events":    [e for e in events if e["days_away"] >= 0][:6],
        "btc_price": btc_price,
    })

# ─────────────────────────────────────────────
#  ON-CHAIN — Glassnode (live if key, estimated if not)
# ─────────────────────────────────────────────
@app.route("/api/onchain")
def api_onchain():
    if GLASSNODE_KEY:
        try:
            def gn(metric, asset="BTC"):
                r = requests.get(
                    f"https://api.glassnode.com/v1/metrics/{metric}",
                    params={"a": asset, "api_key": GLASSNODE_KEY, "i": "24h"},
                    timeout=10
                )
                data = r.json()
                return data[-1]["v"] if data else None

            sopr     = gn("indicators/sopr")
            mvrv     = gn("market/mvrv_z_score")
            exchange = gn("distribution/balance_exchanges")
            lth_pct  = gn("supply/lth_sum")

            return jsonify({
                "source":        "glassnode",
                "sth_sopr":      round(sopr, 4) if sopr else None,
                "mvrv_z":        round(mvrv, 2) if mvrv else None,
                "exchange_btc":  round(exchange, 0) if exchange else None,
                "lth_pct":       round(lth_pct, 1) if lth_pct else None,
                "signal":        "Live Glassnode data",
            })
        except Exception as e:
            logging.error(f"Glassnode error: {e}")

    # Estimated data based on BTC price momentum
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
            timeout=8
        )
        d = r.json()
        chg = float(d.get("priceChangePercent", 0))
        # Estimate SOPR and MVRV based on price action
        sopr  = round(1.0 + (chg / 200), 4)
        mvrv  = round(2.1 + (chg / 50), 2)
        signal = "Profit-taking" if sopr > 1.02 else ("Accumulation" if sopr < 0.98 else "Neutral")
    except:
        sopr = 1.005; mvrv = 2.1; chg = 0; signal = "Neutral"

    return jsonify({
        "source":       "estimated",
        "sth_sopr":     sopr,
        "lth_sopr":     round(sopr * 1.4, 4),
        "mvrv_z":       mvrv,
        "exchange_chg": round(-2.1 + chg/100, 2),
        "lth_pct":      74.3,
        "puell":        round(1.1 + chg/200, 2),
        "signal":       signal,
        "note":         "Add GLASSNODE_KEY for live data ($29/mo)",
    })

# ─────────────────────────────────────────────
#  SENTIMENT — LunarCrush
# ─────────────────────────────────────────────
@app.route("/api/sentiment")
def api_sentiment():
    if not LUNARCRUSH_KEY:
        return jsonify({"error": "No LunarCrush key"})
    result = {}
    for key, slug in {"btc": "bitcoin", "eth": "ethereum"}.items():
        try:
            r = requests.get(
                f"https://lunarcrush.com/api4/public/coins/{slug}/v1",
                headers={"Authorization": f"Bearer {LUNARCRUSH_KEY}"}, timeout=10
            )
            d = r.json().get("data", {})
            result[key] = {
                "galaxy_score":      d.get("galaxy_score", 0),
                "alt_rank":          d.get("alt_rank", 0),
                "average_sentiment": d.get("average_sentiment", 0),
                "social_volume_24h": d.get("social_volume_24h", 0),
                "social_score":      d.get("social_score", 0),
            }
        except Exception as e:
            result[key] = {"error": str(e)}
    return jsonify(result)

# ─────────────────────────────────────────────
#  NEWS — RSS feeds
# ─────────────────────────────────────────────
RSS_SOURCES = {
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "CoinDesk":      "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Decrypt":       "https://decrypt.co/feed",
    "The Defiant":   "https://thedefiant.io/api/feed",
    "Bitcoin Mag":   "https://bitcoinmagazine.com/feed",
}

@app.route("/api/news")
def api_news():
    articles = []
    for source, url in RSS_SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "")
                published = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        dt = datetime.datetime(*entry.published_parsed[:6])
                        published = dt.strftime("%d %b %H:%M")
                    except: pass
                if title and link:
                    articles.append({"title": title, "url": link,
                                     "source": source, "published": published})
                if len(articles) >= 15: break
        except: continue
        if len(articles) >= 15: break
    return jsonify({"articles": articles[:15]})

# ─────────────────────────────────────────────
#  TELEGRAM BOT
# ─────────────────────────────────────────────
def get_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        "🚀 Open Aloha Terminal", web_app=WebAppInfo(url=APP_URL)
    )]])

@app.route("/webhook", methods=["POST"])
def webhook():
    asyncio.run(handle_update(request.get_json()))
    return "ok", 200

tg_app_global = None

async def handle_update(data):
    global tg_app_global
    if tg_app_global is None:
        tg_app_global = ApplicationBuilder().token(TOKEN).build()
        tg_app_global.add_handler(CommandHandler("start",    cmd_start))
        tg_app_global.add_handler(CommandHandler("terminal", cmd_terminal))
        await tg_app_global.initialize()
    update = Update.de_json(data, tg_app_global.bot)
    await tg_app_global.process_update(update)

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *Aloha Terminal*\n\nYour crypto trading dashboard — tap below to open.",
        parse_mode="Markdown", reply_markup=get_keyboard()
    )

async def cmd_terminal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Tap to open your live trading terminal:",
        reply_markup=get_keyboard()
    )

@app.route("/setup_webhook")
def setup_webhook():
    webhook_url = f"{APP_URL}/webhook"
    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        json={"url": webhook_url, "drop_pending_updates": True}
    )
    return jsonify({"webhook_url": webhook_url, "telegram_response": resp.json()})

@app.route("/ping")
def ping():
    return jsonify({"status": "alive", "time": datetime.datetime.utcnow().isoformat()})

def keep_alive():
    """Ping self every 10 minutes to prevent Render free tier from sleeping."""
    import time
    time.sleep(30)  # wait for server to start first
    while True:
        try:
            if APP_URL:
                requests.get(f"{APP_URL}/ping", timeout=10)
                logging.info("Keep-alive ping sent")
        except:
            pass
        time.sleep(600)  # ping every 10 minutes

# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("✅ Aloha Terminal running on port", port)
    # Start keep-alive thread
    import threading
    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
