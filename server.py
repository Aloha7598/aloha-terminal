import json
import os
import threading
import time
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")


def _parse_cors_origins():
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if raw == "*" or not raw:
        return "*"
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


CORS(app, resources={r"/api/*": {"origins": _parse_cors_origins()}})

# =========================================================
# SIMPLE LOCAL DATA
# =========================================================

COIN_CATALOG = [
    {
        "id": "bitcoin-btc",
        "symbol": "BTC",
        "name": "Bitcoin",
        "chain": "Bitcoin",
        "price": 68420.12,
        "change24h": 1.74,
        "liquidity": 1250000000,
        "volume24h": 28900000000,
        "marketCap": 1350000000000,
    },
    {
        "id": "ethereum-eth",
        "symbol": "ETH",
        "name": "Ethereum",
        "chain": "Ethereum",
        "price": 3520.44,
        "change24h": 2.08,
        "liquidity": 820000000,
        "volume24h": 15800000000,
        "marketCap": 422000000000,
    },
    {
        "id": "solana-sol",
        "symbol": "SOL",
        "name": "Solana",
        "chain": "Solana",
        "price": 178.33,
        "change24h": 4.12,
        "liquidity": 390000000,
        "volume24h": 4900000000,
        "marketCap": 79000000000,
    },
    {
        "id": "pepe-eth",
        "symbol": "PEPE",
        "name": "Pepe",
        "chain": "Ethereum",
        "price": 0.0000139,
        "change24h": 7.84,
        "liquidity": 3200000,
        "volume24h": 9800000,
        "marketCap": 5800000000,
    },
    {
        "id": "wif-sol",
        "symbol": "WIF",
        "name": "dogwifhat",
        "chain": "Solana",
        "price": 2.16,
        "change24h": -1.88,
        "liquidity": 1900000,
        "volume24h": 6100000,
        "marketCap": 2200000000,
    },
]

WATCHLIST_STORE = "watchlist.json"
WATCHLIST_LOCK = threading.Lock()

# Small in-memory API cache to reduce external calls/cost.
API_CACHE = {}
CACHE_LOCK = threading.Lock()


# =========================================================
# HELPERS
# =========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def cache_get(key):
    with CACHE_LOCK:
        entry = API_CACHE.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            API_CACHE.pop(key, None)
            return None
        return entry["value"]


def cache_set(key, value, ttl_seconds):
    with CACHE_LOCK:
        API_CACHE[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
        }


def load_watchlist():
    with WATCHLIST_LOCK:
        if os.path.exists(WATCHLIST_STORE):
            try:
                with open(WATCHLIST_STORE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        return []


def save_watchlist(items):
    with WATCHLIST_LOCK:
        try:
            with open(WATCHLIST_STORE, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        except Exception:
            pass


def find_coin(query_text):
    q = (query_text or "").strip().lower()
    if not q:
        return None

    for coin in COIN_CATALOG:
        if coin["symbol"].lower() == q:
            return coin

    for coin in COIN_CATALOG:
        if q in coin["name"].lower() or q in coin["symbol"].lower() or q in coin["id"].lower():
            return coin
    return None


def status_from_score(score):
    if score >= 4:
        return "BREAKOUT"
    if score >= 3:
        return "ACCUMULATION"
    if score == 2:
        return "WAIT"
    return "DISTRIBUTION"


def build_summary(coin):
    change = coin.get("change24h", 0)
    volume = coin.get("volume24h", 0)
    liquidity = coin.get("liquidity", 0)

    supply = "Rising" if change > 0 else "Falling"
    mint_burn = "Positive" if change > 1 else "Negative"
    smart_money = "Not back" if change < 3 else "Returning"
    exchange_flow = "Outflow from CEX" if change > 0 else "Inflow to CEX"

    score = 0
    if change > 0:
        score += 1
    if volume > 10000000:
        score += 1
    if liquidity > 2000000:
        score += 1
    if change > 3:
        score += 1
    if change > 6:
        score += 1

    final_score = min(score, 5)
    return {
        "supply": supply,
        "mintBurn": mint_burn,
        "smartMoney": smart_money,
        "exchangeFlow": exchange_flow,
        "score": final_score,
        "status": status_from_score(final_score),
    }


def build_onchain(coin):
    change = coin.get("change24h", 0)
    market_cap = coin.get("marketCap", 0)

    supply = "Falling" if change < 0 else "Rising"
    mint_burn = "Negative" if change < 1 else "Positive"
    smart_money = "Not back" if change < 2 else "Returning"
    exchange_flow = "Inflow to CEX (risk)" if change < 0 else "Outflow from CEX (bullish)"

    score = 0
    if change > 0:
        score += 1
    if change > 2:
        score += 1
    if market_cap > 1000000000:
        score += 1
    if change > 5:
        score += 1

    return {
        "supply": supply,
        "mintBurn": mint_burn,
        "smartMoney": smart_money,
        "exchangeFlow": exchange_flow,
        "score": min(score, 5),
        "status": "AVOID" if score <= 1 else "WAIT" if score == 2 else "ACCUMULATION",
    }


def build_early_signal(coin):
    change = coin.get("change24h", 0)
    volume = coin.get("volume24h", 0)

    detected = change > 2 or volume > 8000000
    bullets = [
        "Supply +6% (3d)",
        "Whale buys detected",
        "No exchange inflow",
    ]

    if change < 0:
        bullets = [
            "Supply weak",
            "No whale confirmation",
            "Exchange inflow risk",
        ]

    return {
        "detected": detected,
        "bullets": bullets,
        "status": "EARLY ACCUMULATION" if detected else "NO EARLY SIGNAL",
    }


def build_holders(coin):
    change = coin.get("change24h", 0)

    groups = [
        {"label": "Treasury / Multisig", "count": 4},
        {"label": "Exchange Wallets", "count": 2},
        {"label": "Passive Whales", "count": 9},
        {"label": "Active Wallets", "count": 5},
    ]

    new_buyers = {
        "count50k": 2 if change > 1 else 0,
        "count100k": 1 if change > 3 else 0,
        "entries": [
            {"wallet": "0x31...af9", "usd": 54000, "time": "28m ago"},
            {"wallet": "0x88...c12", "usd": 104000, "time": "51m ago"},
            {"wallet": "0x19...d0a", "usd": 67000, "time": "74m ago"},
        ]
        if change > 1
        else [],
    }

    smart_money_returns = {
        "active": change > 3,
        "note": "Fresh capital detected" if change > 3 else "No strong re-accumulation yet",
        "bullets": [
            "Mixed / passive holders",
            "Some exchange deposits",
            "No clustered large re-buys",
        ]
        if change <= 3
        else [
            "Multiple new wallets / large buys clustered in time",
            "Previous sold wallet start accumulating",
            "Average buy size increasing",
        ],
    }

    avg_buy_size = {
        "trend": "Increasing" if change > 2 else "Stable",
        "changePct": 38 if change > 2 else 8,
        "note": "Transactions getting bigger" if change > 2 else "No major change",
    }

    sell_pressure = {
        "trend": "Improving" if change > 0 else "Weak",
        "changePct": -42 if change > 0 else 18,
        "note": "Fewer large red transactions · no big dumps" if change > 0 else "Sell pressure still active",
    }

    exchange_flow = {
        "trend": "Bullish" if change > 0 else "Risk",
        "note": "Exchange outflows > inflows" if change > 0 else "Tokens entering exchanges",
    }

    return {
        "groups": groups,
        "newBuyers": new_buyers,
        "smartMoneyReturns": smart_money_returns,
        "avgBuySize": avg_buy_size,
        "sellPressure": sell_pressure,
        "exchangeFlow": exchange_flow,
    }


def build_coin_detail(coin):
    summary = build_summary(coin)
    onchain = build_onchain(coin)
    early = build_early_signal(coin)
    holders = build_holders(coin)

    context = [
        "BTC trending up → bullish bias",
        "ETH lagging → weak confirmation",
        "No smart money inflow → low conviction",
    ]

    return {
        **coin,
        "summary": summary,
        "onchain": onchain,
        "earlySignal": early,
        "holders": holders,
        "context": context,
    }


def _sanitize_text(value, max_len=64):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _coerce_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _validate_watchlist_payload(payload):
    coin_id = _sanitize_text(payload.get("id"), 100)
    if not coin_id:
        return None, "Missing id"

    cleaned = {
        "id": coin_id,
        "symbol": _sanitize_text(payload.get("symbol"), 24),
        "name": _sanitize_text(payload.get("name"), 64),
        "chain": _sanitize_text(payload.get("chain"), 32),
        "price": _coerce_number(payload.get("price"), 0),
        "change24h": _coerce_number(payload.get("change24h"), 0),
        "status": _sanitize_text(payload.get("status"), 24) or "WAIT",
        "score": int(_coerce_number(payload.get("score"), 0)),
        "early": bool(payload.get("early", False)),
        "updatedAt": now_iso(),
    }
    cleaned["score"] = max(0, min(cleaned["score"], 5))
    return cleaned, None


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/dashboard")
def dashboard():
    return send_from_directory(".", "index.html")


@app.route("/api/prices")
def prices():
    cache_key = "prices"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    try:
        # Use symbol-specific endpoints instead of full ticker list.
        btc_res = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=8,
        )
        eth_res = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "ETHUSDT"},
            timeout=8,
        )
        btc_data = btc_res.json()
        eth_data = eth_res.json()

        result = {
            "BTC-USD": {"price": round(float(btc_data.get("price", 68420.12)), 2)},
            "ETH-USD": {"price": round(float(eth_data.get("price", 3520.44)), 2)},
        }
        cache_set(cache_key, result, ttl_seconds=20)
        return jsonify(result)
    except Exception as e:
        fallback = {
            "BTC-USD": {"price": 68420.12},
            "ETH-USD": {"price": 3520.44},
            "error": str(e),
        }
        cache_set(cache_key, fallback, ttl_seconds=10)
        return jsonify(fallback)


@app.route("/api/signal")
def signal():
    cached = cache_get("signal")
    if cached:
        return jsonify(cached)

    btc_change = -0.9
    fear_greed = 46

    score = 0
    details = []

    if btc_change > 0:
        score += 1
        details.append("BTC trending up")
    else:
        details.append("BTC weak")

    if fear_greed < 40:
        score -= 1
        details.append("Fear market")
    else:
        details.append("Neutral sentiment")

    details.append("ETH lagging")
    details.append("No smart money inflow")

    if score <= -1:
        status = "RISK"
    elif score >= 1:
        status = "BULLISH"
    else:
        status = "WAIT"

    payload = {"status": status, "details": details, "score": score}
    cache_set("signal", payload, ttl_seconds=30)
    return jsonify(payload)


@app.route("/api/smartmoney")
def smartmoney():
    cached = cache_get("smartmoney")
    if cached:
        return jsonify(cached)

    whales = [
        {"label": "Binance Cold Wallet", "amount": 520000, "type": "buy"},
        {"label": "Smart Wallet 0xA1", "amount": 180000, "type": "buy"},
        {"label": "Whale Exit 0xF9", "amount": 90000, "type": "sell"},
    ]

    cex_flow = -1250000

    chip = [
        {"wallet": "0x8f3...a21", "pnl": 245},
        {"wallet": "0x4ab...992", "pnl": 118},
        {"wallet": "0x91c...77d", "pnl": 76},
    ]

    holder_groups = [
        {"label": "Treasury / Multisig", "count": 4, "color": "blue"},
        {"label": "Exchange Wallets", "count": 2, "color": "red"},
        {"label": "Passive Whales", "count": 9, "color": "yellow"},
        {"label": "Active Wallets", "count": 5, "color": "green"},
    ]

    signal_value = "ACCUMULATION" if cex_flow < 0 else "DISTRIBUTION"
    payload = {
        "whales": whales,
        "cex_flow": cex_flow,
        "cex_signal": signal_value,
        "chip": chip,
        "holder_groups": holder_groups,
    }
    cache_set("smartmoney", payload, ttl_seconds=30)
    return jsonify(payload)


@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify({"results": []})

    results = []
    for coin in COIN_CATALOG:
        if q in coin["name"].lower() or q in coin["symbol"].lower() or q in coin["id"].lower():
            results.append(coin)

    if not results:
        for coin in COIN_CATALOG:
            if q in coin["chain"].lower():
                results.append(coin)

    return jsonify({"results": results[:10]})


@app.route("/api/coin/<coin_id>")
def coin_detail(coin_id):
    coin = None
    for item in COIN_CATALOG:
        if item["id"] == coin_id:
            coin = item
            break

    if coin is None:
        q = coin_id.replace("-", " ")
        coin = find_coin(q)

    if coin is None:
        return jsonify({"error": "Coin not found"}), 404

    return jsonify(build_coin_detail(coin))


@app.route("/api/watchlist", methods=["GET", "POST", "DELETE"])
def watchlist():
    items = load_watchlist()

    if request.method == "GET":
        return jsonify({"watchlist": items})

    payload = request.get_json(silent=True) or {}
    clean_payload, err = _validate_watchlist_payload(payload)

    if request.method == "POST":
        if err:
            return jsonify({"error": err}), 400

        existing = next((x for x in items if x.get("id") == clean_payload["id"]), None)
        if existing:
            return jsonify({"ok": True, "message": "Already in watchlist", "watchlist": items})

        items.insert(0, clean_payload)
        save_watchlist(items)
        return jsonify({"ok": True, "watchlist": items})

    if request.method == "DELETE":
        coin_id = _sanitize_text(payload.get("id"), 100)
        if not coin_id:
            return jsonify({"error": "Missing id"}), 400

        items = [x for x in items if x.get("id") != coin_id]
        save_watchlist(items)
        return jsonify({"ok": True, "watchlist": items})

    return jsonify({"error": "Method not allowed"}), 405


@app.route("/ping")
def ping():
    return jsonify({"status": "alive"})


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(_e):
    return jsonify({"error": "Internal server error"}), 500


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
