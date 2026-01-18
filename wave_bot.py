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
    
    # 1. Pivot Points (ප්‍රධාන හැරවුම් ලක්ෂ්‍ය)
    pivots = []
    for i in range(10, len(prices)-10):
        if highs[i] == max(highs[i-5:i+5]): 
            pivots.append({'type': 'High', 'val': highs[i], 'rsi': rsi[i], 'idx': i})
        if lows[i] == min(lows[i-5:i+5]): 
            pivots.append({'type': 'Low', 'val': lows[i], 'rsi': rsi[i], 'idx': i})
    
    if len(pivots) < 6: return "Wave Analyzing...", "Neutral"

    try:
        # Elliott Structure (පසුගිය pivots 5 ලබා ගැනීම)
        p = pivots[-6:]
        w1_high = p[-5]['val']
        w2_low = p[-4]['val']
        w3_high = p[-3]['val']
        w4_low = p[-2]['val']
        w5_high = p[-1]['val']
        
        # RSI values at peaks
        rsi_w3 = p[-3]['rsi']
        rsi_w5 = p[-1]['rsi']

        curr_price = prices[-1]
        msg = "Scanning Patterns..."
        signal = "Neutral"

        # --- Strategy 1: Wave 3 Entry (Fib 0.618) ---
        wave1_dist = abs(p[-5]['val'] - p[-6]['val'])
        fib_618 = w1_high - (wave1_dist * 0.618)
        
        if w2_low >= fib_618 * 0.99 and curr_price > w1_high:
            msg = "🚀 Wave 3 Explosion (Confirmed)"
            signal = "BUY"

        # --- Strategy 2: Wave 5 + RSI Divergence (Top Hunter) ---
        # මිල ඉහළ යද්දී RSI එක පහළ යනවා නම් (Bearish Divergence)
        if w5_high > w3_high and rsi_w5 < rsi_w3:
            msg = "⚠ Wave 5 Divergence (Trend Ending)"
            signal = "SELL"

        # --- Strategy 3: Wave 4 Bounce ---
        if w4_low > w1_high and curr_price > w4_low:
            msg = "🔥 Wave 5 Start (Safe Buy)"
            signal = "BUY"

        return msg, signal
    except:
        return "Detecting Waves...", "Neutral"

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
                alert = f"🌊 ELLIOTT PRO SIGNAL\nPair: {s}\nStatus: {status}\nPrice: ${price}"
                send_telegram(alert)
        
        with placeholder.container():
            st.table(pd.DataFrame(results))
            st.caption(f"Last Update: {time.strftime('%H:%M:%S')}")
        
        time.sleep(60) # විනාඩියකට වරක් පරීක්ෂා කරයි
        st.rerun()
