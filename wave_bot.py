import streamlit as st
import pandas as pd
import time
import numpy as np
from binance.spot import Spot as Client

# --- 1. CONFIGURATION & SECRETS ---
try:
    # Binance Keys (දැනට Read-only වුණත් ගැටලුවක් නැහැ)
    api_key = st.secrets["BINANCE_ACCESS_KEY"]
    api_secret = st.secrets["BINANCE_SECRET_KEY"]
    bot_token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["CHAT_ID"]
    
    client = Client(api_key, api_secret)
except:
    st.error("Streamlit Secrets වල BINANCE_ACCESS_KEY, SECRET_KEY සහ Telegram විස්තර ඇතුළත් කරන්න!")
    st.stop()

def send_telegram(msg):
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={msg}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except: pass

# --- 2. SETTINGS ---
st.set_page_config(page_title="G-Pro Binance Sniper", layout="wide")
st.sidebar.title("⚙️ Binance Strategy Settings")

selected_tf = st.sidebar.selectbox("Timeframe:", ("1m", "5m", "15m", "1h", "4h"), index=1)
rsi_buy = st.sidebar.slider("RSI Buy Limit:", 20, 40, 30)
rsi_sell = st.sidebar.slider("RSI Sell Limit:", 60, 80, 70)
whale_limit = st.sidebar.number_input("Whale Limit ($):", 1000, 100000, 10000)

# --- 3. CORE ANALYTICS ---
def get_binance_data(symbol, interval):
    try:
        # Klines for RSI & Key Levels
        klines = client.klines(symbol, interval, limit=100)
        closes = np.array([float(k[4]) for k in klines])
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        # RSI Calculation
        diff = np.diff(closes)
        up = diff.copy(); up[up < 0] = 0
        down = diff.copy(); down[down > 0] = 0
        avg_gain = np.mean(up[-14:]); avg_loss = abs(np.mean(down[-14:]))
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        # Order Flow & Delta (Trades)
        trades = client.trades(symbol, limit=500)
        b_vol = sum([float(t['qty']) for t in trades if t['isBuyerMaker'] == False])
        s_vol = sum([float(t['qty']) for t in trades if t['isBuyerMaker'] == True])
        delta = b_vol - s_vol
        
        # Key Levels (Support/Resistance)
        sup, res = min(lows[-30:]), max(highs[-30:])
        
        return {
            "price": closes[-1], "rsi": round(rsi, 2), "delta": round(delta, 2),
            "sup": sup, "res": res, "trades": trades
        }
    except Exception as e:
        return None

# --- 4. APP LOOP ---
st.title("🛡️ G-PRO Binance: Ultimate Order Flow Sniper")
coins = st.multiselect("Active Monitor:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "PEPEUSDT"], default=["BTCUSDT", "ETHUSDT"])
placeholder = st.empty()



while True:
    data_list = []
    for s in coins:
        m = get_binance_data(s, selected_tf)
        if not m: continue

        sig, ent, tp, sl = "Scanning 🔍", 0, 0, 0
        
        # BUY Logic: Oversold + Positive Delta + Support
        if m['rsi'] < rsi_buy and m['delta'] > 0 and m['price'] <= m['sup'] * 1.002:
            sig = "🚀 BUY SIGNAL"
            ent = m['price']
            sl = m['sup'] * 0.995; tp = ent + (ent - sl) * 2.0
            send_telegram(f"🔥 *BINANCE BUY: {s}*\nPrice: {ent}\nTP: {round(tp,2)}\nSL: {round(sl,2)}\nRSI: {m['rsi']}")

        # SELL Logic: Overbought + Negative Delta + Resistance
        elif m['rsi'] > rsi_sell and m['delta'] < 0 and m['price'] >= m['res'] * 0.998:
            sig = "📉 SELL SIGNAL"
            ent = m['price']
            sl = m['res'] * 1.005; tp = ent - (sl - ent) * 2.0
            send_telegram(f"📉 *BINANCE SELL: {s}*\nPrice: {ent}\nTP: {round(tp,2)}\nSL: {round(sl,2)}\nRSI: {m['rsi']}")

        data_list.append({
            "Pair": s, "Price": m['price'], "RSI": m['rsi'], "Delta": m['delta'], "Status": sig
        })

    with placeholder.container():
        st.table(pd.DataFrame(data_list))
        st.caption(f"Last Update: {time.strftime('%H:%M:%S')} | Binance Live Feed")
    
    time.sleep(10)
