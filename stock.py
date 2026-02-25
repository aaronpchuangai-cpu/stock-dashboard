import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="全球量化策略儀表板", layout="wide")
st.title("🌎 全球股票技術分析與策略回測儀表板")

# --- 2. 快取功能：避免頻繁請求被 Yahoo 封鎖 ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1y")
        return data
    except Exception:
        return pd.DataFrame()

# --- 3. 側邊欄控制區塊 (Sidebar) ---
st.sidebar.header("📊 基礎參數設定")
stock_id = st.sidebar.text_input("股票代號 (台股加 .TW，美股直接輸入)", "NVDA")
initial_capital = st.sidebar.number_input("初始投資本金 (單位視股票市場而定)", value=1000000, step=100000)
cost_input = st.sidebar.number_input("單次交易摩擦成本 (%)", value=0.20, step=0.05)
cost_pct = cost_input / 100

# --- 【新增】美股常用工具連結 ---
st.sidebar.markdown("---")
st.sidebar.header("🔗 常用工具連結")
st.sidebar.markdown("[Yahoo Finance (查詢美股代號)](https://finance.yahoo.com/)")
st.sidebar.markdown("[TradingView (國際專業圖表)](https://www.tradingview.com/)")
st.sidebar.info("💡 提示：輸入 AAPL (蘋果)、NVDA (輝達)、TSLA (特斯拉) 即可觀察美股指標。")

st.sidebar.markdown("---")
st.sidebar.header("🚀 投資策略組合")
strategy_option = st.sidebar.selectbox(
    "請選擇均線交叉組合",
    ["5MA / 20MA (短線順勢)", "5MA / 10MA (極短線)", "20MA / 60MA (中長線波段)", "自定義短均線 / 長均線"]
)

if strategy_option == "5MA / 20MA (短線順勢)":
    short_p, long_p = 5, 20
elif strategy_option == "5MA / 10MA (極短線)":
    short_p, long_p = 5, 10
elif strategy_option == "20MA / 60MA (中長線波段)":
    short_p, long_p = 20, 60
else:
    col_s, col_l = st.sidebar.columns(2)
    short_p = col_s.number_input("短線天數", value=10, min_value=1)
    long_p = col_l.number_input("長線天數", value=30, min_value=2)

# --- 4. 主要計算邏輯 ---
if stock_id:
    df = get_stock_data(stock_id)
    
    if df.empty:
        st.warning("目前抓不到資料。請確認代號是否正確，或稍後再試。")
    else:
        df['Short_MA'] = df['Close'].rolling(window=short_p).mean()
        df['Long_MA'] = df['Close'].rolling(window=long_p).mean()
        
        st.markdown(f"### {stock_id} 技術線圖 ({short_p}MA / {long_p}MA)")
        fig, ax1 = plt.subplots(figsize=(14, 5))
        ax1.plot(df.index, df['Close'], label='收盤價', color='dodgerblue', alpha=0.5)
        ax1.plot(df.index, df['Short_MA'], label=f'{short_p}MA', color='orange', linewidth=1.5)
        ax1.plot(df.index, df['Long_MA'], label=f'{long_p}MA', color='red', linewidth=1.5)
        ax1.legend()
        ax1.grid(True, alpha=0.2)
        st.pyplot(fig)

        # --- 回測運算 ---
        df['Signal'] = np.where(df['Short_MA'] > df['Long_MA'], 1, 0)
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        df['Market_Return'] = df['Close'].pct_change()
        df['Strategy_Return_No_Cost'] = df['Signal'].shift(1) * df['Market_Return']
        df['Cum_Strategy_No_Cost'] = (1 + df['Strategy_Return_No_Cost'].fillna(0)).cumprod()
        df['Accum_Cost'] = (df['Trade'] * cost_pct * initial_capital).cumsum()
        df['Account_Strategy'] = (initial_capital * df['Cum_Strategy_No_Cost']) - df['Accum_Cost']
        df['Account_Market'] = initial_capital * (1 + df['Market_Return']).cumprod()
        
        # 數據結算
        final_market = df['Account_Market'].dropna().iloc[-1]
        final_strategy = df['Account_Strategy'].dropna().iloc[-1]
        total_cost = df['Accum_Cost'].iloc[-1]
        total_trades = int(df['Trade'].sum())

        st.markdown("---")
        st.markdown(f"### 💰 策略結算 (投入本金：{initial_capital:,})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("策略期末總額", f"${final_strategy:,.0f}")
        c2.metric("死抱不放總額", f"${final_market:,.0f}")
        c3.metric("累計摩擦成本", f"${total_cost:,.0f}", delta=f"交易 {total_trades} 次", delta_color="inverse")
        net_profit = final_strategy - initial_capital
        c4.metric("策略淨獲利", f"${net_profit:,.0f}", delta=f"{(net_profit/initial_capital)*100:.1f}%")

        st.markdown("#### 📊 資金成長曲線走勢")
        fig2, ax2 = plt.subplots(figsize=(14, 5))
        ax2.plot(df.index, df['Account_Market'], label='Buy & Hold', color='gray', alpha=0.4)
        ax2.plot(df.index, df['Account_Strategy'], label='Strategy (含成本)', color='red', linewidth=2.5)
        ax2.axhline(initial_capital, color='black', linestyle='-', alpha=0.3)
        ax2.set_ylabel("Account Balance")
        ax2.legend()
        ax2.grid(True, alpha=0.2)
        ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        st.pyplot(fig2)