# Aloha Terminal — Telegram Mini App

## What you get
- Live crypto prices (BTC, ETH, SOL, BNB + more)
- BTC & ETH Spot ETF tracker
- On-chain signals (STH SOPR, MVRV, exchange flows)
- Risk dashboard (liquidations, funding rate, volatility)
- Social sentiment (LunarCrush Galaxy Score, AltRank)
- Live news from 5 crypto sources
- AI-generated trading signal based on live data

---

## Setup (step by step)

### Step 1 — Fill in your keys in server.py
Open `server.py` in Notepad and fill in these 4 lines at the top:

```python
TOKEN          = "your telegram bot token"     # from @BotFather
LUNARCRUSH_KEY = "your lunarcrush key"         # free at lunarcrush.com/developers
NEWS_API_KEY   = "your newsapi key"            # free at newsapi.org (optional)
CHAT_ID        = "your chat id"               # from @userinfobot
APP_URL        = ""                           # fill in AFTER deploying (step 3)
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Deploy to Railway (free)
1. Create a free account at **railway.app**
2. Click **New Project → Deploy from GitHub**
3. Push this folder to a GitHub repo first:
   ```bash
   git init
   git add .
   git commit -m "aloha terminal"
   git push
   ```
4. In Railway dashboard → add your environment variables:
   - `TOKEN` = your telegram token
   - `LUNARCRUSH_KEY` = your lunarcrush key
   - `NEWS_API_KEY` = your newsapi key
   - `CHAT_ID` = your chat id
5. Railway gives you a public URL like `https://your-app.railway.app`
6. Copy that URL and paste it as `APP_URL` in your Railway env vars

### Step 4 — Test locally first (optional)
```bash
# Install ngrok for a temporary public URL
# Download from ngrok.com, then:
ngrok http 8080

# Copy the https URL ngrok gives you
# Paste it as APP_URL in server.py
# Then run:
python server.py
```

### Step 5 — Open in Telegram
1. Message your bot on Telegram
2. Send `/start`
3. Tap the **"Open Aloha Terminal"** button
4. The full dashboard opens inside Telegram!

---

## API Keys (all free to start)

| Key | Where to get it | Cost |
|-----|----------------|------|
| Telegram token | @BotFather | Free |
| LunarCrush | lunarcrush.com/developers | Free tier |
| NewsAPI | newsapi.org | Free tier |
| Chat ID | @userinfobot | Free |

## Upgrade for more data (optional)
| Service | Cost | Adds |
|---------|------|------|
| Glassnode | $29/mo | Real STH SOPR, MVRV, on-chain |
| CoinGlass | $35/mo | Live liquidations, funding rates |
| LunarCrush Pro | $49/mo | More API calls |
