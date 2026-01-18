import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client
import time
import requests

# --- Settings & Secrets ---
try:
    api_key = st.secrets["BINANCE_API_KEY"]
    api_secret = st.secrets["BINANCE_API_SECRET"]
    bot_token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["CHAT_ID"]
except:
    st.error("Secrets missing! Check Streamlit Cloud Settings.")
    st.stop()

client = Client(api_key, api_secret, tld='us')

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={msg}"
        requests.get(url, timeout=10)
    except: pass

st.set_page_config(page_title="Elliott Pro v2", page_icon="🌊", layout="wide")
st.title("🛡 G-Pro: Ultimate Elliott Wave Scanner (v2.0)")

def calculate_rsi(df, period=14):
    delta = df['C'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_data(symbol, interval):
    k = client.get_klines(symbol=symbol, interval=interval, limit=200)
    df = pd.DataFrame(k, columns=['T','O','H','L','C','V','CT','Q','Tr','TB','TQ','I'])
    df[['H','L','C']] = df[['H','L','C']].astype(float)
    df['RSI'] = calculate_rsi(df)
    return df

def analyze_pro(df):
    highs = df['H'].values
    lows = df['L'].values
    prices = df['C'].values
    rsi = df['RSI'].values
    
    pivots = []
    for i in range(10, len(prices)-10):
        if highs[i] == max(highs[i-5:i+5]): 
            pivots.append({'type': 'High', 'val': highs[i], 'rsi': rsi[i], 'idx': i})
        if lows[i] == min(lows[i-5:i+5]): 
            pivots.append({'type': 'Low', 'val': lows[i], 'rsi': rsi[i], 'idx': i})
    
    if len(pivots) < 6: return "Analyzing...", "Neutral", 0, 0, 0

    try:
        p = pivots[-6:]
        w1_high, w2_low, w3_high, w4_low = p[-5]['val'], p[-4]['val'], p[-3]['val'], p[-2]['val']
        curr_price = prices[-1]
        
        entry, tp, sl = 0, 0, 0
        msg, signal = "Scanning...", "Neutral"

        # --- Strategy: Wave 3 Explosion (The Best Entry) ---
        wave1_dist = abs(w1_high - p[-6]['val'])
        fib_618 = w1_high - (wave1_dist * 0.618)

        if curr_price > w1_high and w2_low >= fib_618 * 0.99:
            entry = curr_price
            sl = w2_low * 0.995 # Wave 2 පහළට වඩා මදක් අඩුවෙන්
            tp = entry + (wave1_dist * 1.618) # Wave 3 ඉලක්කය (1.618 extension)
            msg = "🚀 WAVE 3 BUY"
            signal = "BUY"

        # --- Strategy: Wave 5 Entry ---
        elif curr_price > w3_high and w4_low > w1_high:
            entry = curr_price
            sl = w4_low * 0.995
            tp = entry + (abs(w3_high - w2_low) * 0.618)
            msg = "🔥 WAVE 5 BUY"
            signal = "BUY"

        return msg, signal, round(entry, 4), round(tp, 4), round(sl, 4)
    except:
        return "Detecting...", "Neutral", 0, 0, 0
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOTUSDT', 'MATICUSDT']
tf = st.sidebar.selectbox("Timeframe", ['15m', '1h', '4h'])

if st.sidebar.button("Launch Pro Scanner"):
    st.info(f"Bot Active: Scanning for Elliott Waves & Divergences on {tf}")
    placeholder = st.empty()
    
    while True:
        results = []
        for s in symbols:
            df = get_market_data(s, tf)
            status, sig_type = analyze_pro(df)
            price = df.iloc[-1]['C']
            
            results.append({"Pair": s, "Price": price, "Elliott Status": status})
            
            # Telegram Alerts for signals
            if sig_type != "Neutral":
    alert = (f"🌊 ELLIOTT PRO SIGNAL\n\n"
             f"🪙 Pair: {s}\n"
             f"📊 Status: {status}\n"
             f"✅ *ENTRY: {entry}*\n"
             f"🎯 *TP: {tp}*\n"
             f"🛑 *SL: {sl}*")
    send_telegram(alert)
        
        with placeholder.container():
            st.table(pd.DataFrame(results))
            st.caption(f"Last Update: {time.strftime('%H:%M:%S')}")
        
        time.sleep(60) # විනාඩියකට වරක් පරීක්ෂා කරයි
        st.rerun()
