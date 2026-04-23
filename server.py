import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# =========================
# API BASE
# =========================
BINANCE = "https://api.binance.com/api/v3/ticker/24hr"

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return dashboard()

@app.route("/dashboard")
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Aloha Terminal</title>
<style>
body { background:#0a0a0f; color:white; font-family:sans-serif; }
.nav { display:flex; gap:20px; padding:10px; }
.nav-item { cursor:pointer; opacity:.5; }
.nav-item.active { opacity:1; color:#00e5a0; }

.section { display:none; padding:10px; }
.section.active { display:block; }

.card { background:#111; padding:10px; margin-bottom:10px; border-radius:8px; }
.green { color:#00e5a0 }
.red { color:#ff4466 }
</style>
</head>

<body>

<h2>ALOHA TERMINAL</h2>

<div class="nav">
  <div class="nav-item active" onclick="tab('overview', this)">Overview</div>
  <div class="nav-item" onclick="tab('etf', this)">ETF</div>
  <div class="nav-item" onclick="tab('onchain', this)">OnChain</div>
  <div class="nav-item" onclick="tab('risk', this)">Risk</div>
  <div class="nav-item" onclick="tab('sentiment', this)">Sentiment</div>
  <div class="nav-item" onclick="tab('news', this)">News</div>
</div>

<div id="sec-overview" class="section active">
  <div class="card">
    <h3>Prices</h3>
    <div id="btc">Loading...</div>
    <div id="eth">Loading...</div>
  </div>
</div>

<div id="sec-etf" class="section">
  <div class="card" id="etf">Loading ETF...</div>
</div>

<div id="sec-onchain" class="section">
  <div class="card" id="onchain">Loading Onchain...</div>
</div>

<div id="sec-risk" class="section">
  <div class="card" id="risk">Loading Risk...</div>
</div>

<div id="sec-sentiment" class="section">
  <div class="card" id="sentiment">Loading Sentiment...</div>
</div>

<div id="sec-news" class="section">
  <div class="card" id="news">Loading News...</div>
</div>

<script>
const API = window.location.origin;

// TAB SWITCH
function tab(name, el) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));

  el.classList.add('active');
  document.getElementById('sec-' + name).classList.add('active');

  if (name === 'etf') loadETF();
  if (name === 'onchain') loadOnchain();
  if (name === 'risk') loadRisk();
  if (name === 'sentiment') loadSentiment();
  if (name === 'news') loadNews();
}

// =========================
// LOADERS
// =========================
async function loadPrices() {
  const r = await fetch(API + "/api/prices");
  const d = await r.json();

  document.getElementById('btc').innerText = "BTC: $" + d.BTC;
  document.getElementById('eth').innerText = "ETH: $" + d.ETH;
}

async function loadETF() {
  const r = await fetch(API + "/api/etf");
  const d = await r.json();
  document.getElementById('etf').innerText = JSON.stringify(d, null, 2);
}

async function loadOnchain() {
  const r = await fetch(API + "/api/onchain");
  const d = await r.json();
  document.getElementById('onchain').innerText = JSON.stringify(d, null, 2);
}

async function loadRisk() {
  const r = await fetch(API + "/api/risk");
  const d = await r.json();
  document.getElementById('risk').innerText = JSON.stringify(d, null, 2);
}

async function loadSentiment() {
  const r = await fetch(API + "/api/sentiment");
  const d = await r.json();
  document.getElementById('sentiment').innerText = JSON.stringify(d, null, 2);
}

async function loadNews() {
  const r = await fetch(API + "/api/news");
  const d = await r.json();
  document.getElementById('news').innerText = JSON.stringify(d, null, 2);
}

// INIT
loadPrices();
</script>

</body>
</html>
"""

# =========================
# APIs
# =========================
@app.route("/api/prices")
def prices():
    r = requests.get(BINANCE).json()
    data = {t["symbol"]: t for t in r}

    return jsonify({
        "BTC": float(data["BTCUSDT"]["lastPrice"]),
        "ETH": float(data["ETHUSDT"]["lastPrice"])
    })

@app.route("/api/etf")
def etf():
    return jsonify({"btc_flow": "positive", "eth_flow": "neutral"})

@app.route("/api/onchain")
def onchain():
    return jsonify({"sopr": 1.01, "mvrv": 2.2})

@app.route("/api/risk")
def risk():
    return jsonify({"fear_greed": 46})

@app.route("/api/sentiment")
def sentiment():
    return jsonify({"btc_sentiment": "neutral"})

@app.route("/api/news")
def news():
    return jsonify({"headline": "BTC market stable"})

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
