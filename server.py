import os
import requests
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')

# =========================
# ROUTES
# =========================

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'index.html')


# =========================
# API: PRICES
# =========================
@app.route('/api/prices')
def prices():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price")
        data = r.json()

        result = {}
        for x in data:
            if x['symbol'] == 'BTCUSDT':
                result['BTC-USD'] = {'price': round(float(x['price']), 2)}
            if x['symbol'] == 'ETHUSDT':
                result['ETH-USD'] = {'price': round(float(x['price']), 2)}

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


# =========================
# API: SIGNAL
# =========================
@app.route('/api/signal')
def signal():
    return jsonify({
        "status": "NEUTRAL",
        "message": "BTC stable, no clear edge."
    })


# =========================
# API: SMART MONEY
# =========================
@app.route('/api/smartmoney')
def smartmoney():
    return jsonify({
        "whales": [
            {"label": "Binance Cold Wallet", "amount": 520000, "type": "buy"},
            {"label": "Smart Wallet 0xA1", "amount": 180000, "type": "buy"},
            {"label": "Whale Exit 0xF9", "amount": 90000, "type": "sell"}
        ],
        "cex_flow": -1250000,
        "chip": [
            {"wallet": "0x8f3...a21", "pnl": 245},
            {"wallet": "0x4ab...992", "pnl": 118},
            {"wallet": "0x91c...77d", "pnl": 76}
        ]
    })


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
