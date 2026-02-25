import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. 網頁風格與快取 ---
st.set_page_config(page_title="Global Quant Expert", layout="wide")

@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1y")
        return data
    except Exception:
        return pd.DataFrame()

# 計算 RSI 的函式
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 2. 側邊欄控制面板 ---
st.sidebar.header("📊 全球標的設定")
# 支援多標的輸入
input_ids = st.sidebar.text_input("請輸入股票代號 (用逗號隔開)", "NVDA, AAPL, 2330.TW, TSLA")
stock_list = [s.strip().upper() for s in input_ids.split(",")]
target_stock = st.sidebar.selectbox("🎯 當前分析標的", stock_list)

initial_capital = st.sidebar.number_input("初始本金", value=1000000)
cost_pct = st.sidebar.number_input("摩擦成本 (%)", value=0.20) / 100

st.sidebar.markdown("---")
st.sidebar.header("🚀 策略與濾網")
strategy_option = st.sidebar.selectbox("均線組合", ["5MA / 20MA", "20MA / 60MA", "自定義"])

if strategy_option == "5MA / 20MA":
    short_p, long_p = 5, 20
elif strategy_option == "20MA / 60MA":
    short_p, long_p = 20, 60
else:
    c1, c2 = st.sidebar.columns(2)
    short_p = c1.number_input("短均", 1, 100, 10)
    long_p = c2.number_input("長均", 2, 200, 30)

use_rsi_filter = st.sidebar.checkbox("啟用 RSI 濾網 (避免高點追價)", value=True)
rsi_limit = st.sidebar.slider("RSI 進場上限 (預設70)", 50, 90, 70)

# --- 3. 數據核心運算 ---
if target_stock:
    df = get_stock_data(target_stock)
    
    if not df.empty:
        # 指標計算
        df['Short_MA'] = df['Close'].rolling(window=short_p).mean()
        df['Long_MA'] = df['Close'].rolling(window=long_p).mean()
        df['RSI'] = calculate_rsi(df['Close'])
        
        # 基礎均線訊號
        df['MA_Signal'] = np.where(df['Short_MA'] > df['Long_MA'], 1, 0)
        
        # 套用 RSI 濾網：若 MA 轉多頭但 RSI 太高，則不進場
        if use_rsi_filter:
            df['Signal'] = np.where((df['MA_Signal'] == 1) & (df['RSI'] < rsi_limit), 1, 0)
        else:
            df['Signal'] = df['MA_Signal']
            
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        df['Market_Return'] = df['Close'].pct_change()
        df['Strategy_Return'] = (df['Signal'].shift(1) * df['Market_Return']) - (df['Trade'] * cost_pct)
        
        # 資金與 MDD
        df['Account_Strategy'] = initial_capital * (1 + df['Strategy_Return'].fillna(0)).cumprod()
        df['Account_Market'] = initial_capital * (1 + df['Market_Return'].fillna(0)).cumprod()
        df['Strategy_Peak'] = df['Account_Strategy'].cummax()
        df['Drawdown'] = (df['Account_Strategy'] - df['Strategy_Peak']) / df['Strategy_Peak']
        
        # --- 4. 畫面呈現 ---
        st.title(f"🛡️ {target_stock} 策略深度分析")
        
        final_strategy = df['Account_Strategy'].iloc[-1]
        mdd = df['Drawdown'].min() * 100
        roi = ((final_strategy - initial_capital) / initial_capital) * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("策略最終資產", f"${final_strategy:,.0f}")
        c2.metric("累積報酬率", f"{roi:.2f}%")
        c3.metric("最大回撤 (MDD)", f"{mdd:.2f}%", delta_color="inverse")
        c4.metric("總交易次數", f"{int(df['Trade'].sum())} 次")

        st.markdown("---")
        t1, t2, t3 = st.tabs(["📊 技術圖表", "💰 資金與回撤", "🧬 策略邏輯檢視"])
        
        with t1:
            # 價格與均線圖
            fig, (ax1, ax_rsi) = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [3, 1]})
            ax1.plot(df.index, df['Close'], color='gray', alpha=0.3, label='Price')
            ax1.plot(df.index, df['Short_MA'], color='orange', label=f'{short_p}MA')
            ax1.plot(df.index, df['Long_MA'], color='red', label=f'{long_p}MA')
            ax1.set_title("Price & Moving Averages")
            ax1.legend()
            
            # RSI 圖
            ax_rsi.plot(df.index, df['RSI'], color='purple', label='RSI')
            ax_rsi.axhline(rsi_limit, color='red', linestyle='--', alpha=0.5) # 超買界線
            ax_rsi.axhline(30, color='green', linestyle='--', alpha=0.5) # 超賣界線
            ax_rsi.fill_between(df.index, y1=rsi_limit, y2=100, color='red', alpha=0.1)
            ax_rsi.set_ylim(0, 100)
            ax_rsi.set_ylabel("RSI")
            st.pyplot(fig)

        with t2:
            fig2, ax2 = plt.subplots(figsize=(16, 6))
            ax2.plot(df.index, df['Account_Market'], label='Market (B&H)', color='gray', alpha=0.5)
            ax2.plot(df.index, df['Account_Strategy'], label='Strategy', color='blue', linewidth=2)
            ax2.fill_between(df.index, df['Account_Strategy'], initial_capital, alpha=0.1)
            ax2.legend()
            st.pyplot(fig2)
            
        with t3:
            st.write("最後五筆交易數據明細：")
            st.dataframe(df[['Close', 'Short_MA', 'Long_MA', 'RSI', 'Signal']].tail(10))
            st.info(f"💡 目前狀態：{'🟢 持有中' if df['Signal'].iloc[-1] == 1 else '⚪ 空手觀望'}")