import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
import pandas as pd
import requests

# Page එකේ නම
st.set_page_config(page_title="My Python TradingView", layout="wide")
st.title("📈 My Python Trading Chart (BTC/USDT)")

# 1. Binance එකෙන් Data ලබාගැනීම
def get_crypto_data(symbol="BTCUSDT"):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    data = requests.get(url).json()
    
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    
    # TradingView එකට අවශ්‍ය විදිහට දත්ත සකස් කිරීම
    chart_data = []
    for index, row in df.iterrows():
        chart_data.append({
            "time": int(row['time'] / 1000), # Unix timestamp
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        })
    return chart_data

# 2. ප්‍රස්ථාරයේ පෙනුම සකස් කිරීම (Chart Options)
chartOptions = {
    "layout": {
        "textColor": 'white',
        "background": { "type": 'solid', "color": '#131722' },
    },
    "grid": {
        "vertLines": { "color": '#242733' },
        "horzLines": { "color": '#242733' },
    },
}

# 3. ප්‍රස්ථාරය ඇඳීම
data = get_crypto_data()
seriesCandlestickChart = [{
    "type": 'Candlestick',
    "data": data,
    "options": {
        "upColor": '#26a69a',
        "downColor": '#ef5350',
        "borderVisible": False,
        "wickUpColor": '#26a69a',
        "wickDownColor": '#ef5350',
    }
}]

# Screen එකේ Chart එක පෙන්වීම
renderLightweightCharts([
    {
        "chart": chartOptions,
        "series": seriesCandlestickChart
    }
], 'candlestick')

st.success("Binance වෙතින් සජීවී දත්ත ලබාගන්නා ලදී!")
