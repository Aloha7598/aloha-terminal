import os
import json
import logging
import datetime
import threading
import requests
import feedparser
import yfinance as yf
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
TOKEN          = os.environ.get("TOKEN", "")
LUNARCRUSH_KEY = os.environ.get("LUNARCRUSH_KEY", "")
NEWS_API_KEY   = os.environ.get("NEWS_API_KEY", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
APP_URL        = os.environ.get("APP_URL", "")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# ─────────────────────────────────────────────
#  FLASK APP
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder=".")
CORS(app)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# ─── PRICES ───
CRYPTO_SYMBOLS = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","DOGE-USD","ADA-USD","AVAX-USD"]

@app.route("/api/prices")
def api_prices():
    data = {}
    for sym in CRYPTO_SYMBOLS:
        try:
            info  = yf.Ticker(sym).fast_info
            price = info.last_price
            prev  = info.previous_close
            pct   = ((price - prev) / prev) * 100
            data[sym] = {"price": round(price, 6), "change_pct": round(pct, 2)}
        except Exception as e:
            data[sym] = {"price": 0, "change_pct": 0, "error": str(e)}
    return jsonify(data)

# ─── ETF DATA ───
BTC_ETFS = {"IBIT":"BlackRock IBIT","FBTC":"Fidelity FBTC","BITB":"Bitwise BITB",
            "ARKB":"ARK 21Shares","BTCO":"Invesco BTCO","HODL":"VanEck HODL",
            "GBTC":"Grayscale GBTC","EZBC":"Franklin EZBC"}
ETH_ETFS = {"ETHA":"BlackRock ETHA","FETH":"Fidelity FETH","ETHW":"Bitwise ETHW",
            "CETH":"21Shares CETH","ETHV":"VanEck ETHV","ETHE":"Grayscale ETHE"}

def fetch_etf_group(etf_map):
    results = []
    for ticker, name in etf_map.items():
        try:
            info  = yf.Ticker(ticker).fast_info
            price = info.last_price
            prev  = info.previous_close
            pct   = ((price - prev) / prev) * 100
            vol   = int(info.three_month_average_volume or 0)
            results.append({"ticker": ticker, "name": name,
                           "price": round(price, 2), "change_pct": round(pct, 2), "volume": vol})
        except:
            pass
    return results

@app.route("/api/etfs")
def api_etfs():
    return jsonify({"btc": fetch_etf_group(BTC_ETFS), "eth": fetch_etf_group(ETH_ETFS)})

# ─── SENTIMENT ───
LC_BASE = "https://lunarcrush.com/api4/public"
COIN_SLUGS = {"bitcoin": "bitcoin", "ethereum": "ethereum"}

@app.route("/api/sentiment")
def api_sentiment():
    if not LUNARCRUSH_KEY or LUNARCRUSH_KEY == "PASTE_YOUR_LUNARCRUSH_KEY":
        return jsonify({"error": "No LunarCrush key"})
    result = {}
    for key, slug in COIN_SLUGS.items():
        try:
            r = requests.get(f"{LC_BASE}/coins/{slug}/v1",
                           headers={"Authorization": f"Bearer {LUNARCRUSH_KEY}"}, timeout=10)
            d = r.json().get("data", {})
            result[key[:3]] = {
                "galaxy_score":       d.get("galaxy_score", 0),
                "alt_rank":           d.get("alt_rank", 0),
                "average_sentiment":  d.get("average_sentiment", 0),
                "social_volume_24h":  d.get("social_volume_24h", 0),
                "social_score":       d.get("social_score", 0),
            }
        except Exception as e:
            result[key[:3]] = {"error": str(e)}
    return jsonify(result)

# ─── NEWS ───
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
                    except:
                        pass
                if title and link:
                    articles.append({"title": title, "url": link,
                                   "source": source, "published": published})
                if len(articles) >= 15:
                    break
        except:
            continue
        if len(articles) >= 15:
            break
    return jsonify({"articles": articles[:15]})

# ─────────────────────────────────────────────
#  TELEGRAM BOT via WEBHOOK
# ─────────────────────────────────────────────
import asyncio
from telegram import Bot

def get_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        "🚀 Open Aloha Terminal",
        web_app=WebAppInfo(url=APP_URL)
    )]])

@app.route(f"/webhook", methods=["POST"])
def webhook():
    from flask import request
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
        parse_mode="Markdown",
        reply_markup=get_keyboard()
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
    result = resp.json()
    return jsonify({"webhook_url": webhook_url, "telegram_response": result})

# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("✅ Aloha Terminal running on port", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
