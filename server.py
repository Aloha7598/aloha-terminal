import os
import requests
from flask import Flask, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
BINANCE = "https://api.binance.com/api/v3/ticker/24hr"

# =========================
# SERVE FRONTEND
# =========================
@app.route("/")
def home():
    return send_file("index.html")

# =========================
# PRICES API
# =========================
@app.route("/api/prices")
def prices():
    try:
        r = requests.get(BINANCE, timeout=5)
        data = r.json()

        ticker = {t["symbol"]: t for t in data}

        return jsonify({
            "BTC": float(ticker["BTCUSDT"]["lastPrice"]),
            "ETH": float(ticker["ETHUSDT"]["lastPrice"])
        })
    except:
        return jsonify({
            "BTC": 0,
            "ETH": 0
        })

# =========================
# SMART MONEY (MOCK DATA)
# =========================
@app.route("/api/smartmoney")
def smartmoney():
    return jsonify({
        "cex_flow": -1250000,  # negative = accumulation
        "whales": [
            {"type": "buy", "label": "Binance Cold Wallet", "amount": 520000},
            {"type": "buy", "label": "Smart Wallet 0xA1", "amount": 180000},
            {"type": "sell", "label": "Whale Exit 0xF9", "amount": 90000}
        ],
        "chip": [
            {"wallet": "0x8f3...a21", "pnl": 245},
            {"wallet": "0x4ab...992", "pnl": 118},
            {"wallet": "0x91c...77d", "pnl": 76}
        ]
    })

# =========================
# HEALTH CHECK
# =========================
@app.route("/ping")
def ping():
    return jsonify({"status": "alive"})

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
