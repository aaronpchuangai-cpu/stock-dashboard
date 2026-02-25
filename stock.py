import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="量化交易儀表板", layout="wide")
st.title("📈 專屬股票技術分析與真實本金回測")

# --- 2. 快取功能：解決 YFRateLimitError (最重要的防護) ---
@st.cache_data(ttl=3600)  # 資料緩存1小時，避免頻繁請求被 Yahoo 封鎖
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1y")
        return data
    except Exception:
        return pd.DataFrame()

# --- 3. 使用者輸入區塊 ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    stock_id = st.text_input("請輸入股票代號 (例如: 2330.TW)", "2330.TW")
with col_b:
    initial_capital = st.number_input("請輸入初始本金", value=1000000, step=100000)
with col_c:
    cost_input = st.number_input("單次交易成本 (%)", value=0.20, step=0.05)
    cost_pct = cost_input / 100

st.markdown("### ⚙️ 技術指標顯示設定：")
col1, col2, col3, col4, col5 = st.columns(5)
with col1: show_5ma = st.checkbox("顯示 5MA", value=True)
with col2: show_10ma = st.checkbox("顯示 10MA", value=False)
with col3: show_20ma = st.checkbox("顯示 20MA", value=True)
with col4: show_60ma = st.checkbox("顯示 60MA", value=False)
with col5: show_bb = st.checkbox("顯示 布林通道", value=False)

# --- 4. 主要邏輯判斷 ---
if stock_id:
    df = get_stock_data(stock_id)
    
    if df.empty:
        st.warning("目前抓不到資料，可能是輸入錯誤或 Yahoo 暫時連線過多，請稍後幾分鐘再重新整理網頁。")
    else:
        # 計算技術指標
        df['5MA']  = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        # 繪製上半部 K 線與均線圖
        fig, ax1 = plt.subplots(figsize=(14, 6))
        ax1.plot(df.index, df['Close'], label='收盤價 (Close)', color='dodgerblue', alpha=0.8)
        if show_5ma: ax1.plot(df.index, df['5MA'], label='5MA', color='orange')
        if show_10ma: ax1.plot(df.index, df['10MA'], label='10MA', color='purple')
        if show_20ma: ax1.plot(df.index, df['20MA'], label='20MA', color='red')
        if show_60ma: ax1.plot(df.index, df['60MA'], label='60MA', color='green')
        
        ax1.set_title(f"{stock_id} 歷史走勢", fontsize=15)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        st.pyplot(fig)

        # --- 5. 回測運算系統 (含摩擦成本) ---
        st.markdown("---")
        st.markdown(f"### 💰 5MA/20MA 交叉策略回測 (本金：{initial_capital:,} 元)")
        
        # 產生訊號與偵測交易
        df['Signal'] = np.where(df['5MA'] > df['20MA'], 1, 0)
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        
        # 計算報酬率
        df['Market_Return'] = df['Close'].pct_change()
        # 核心公式：策略獲利 = (持倉狀態 * 漲跌幅) - (交易動作 * 成本)
        df['Strategy_Return'] = (df['Signal'].shift(1) * df['Market_Return']) - (df['Trade'] * cost_pct)
        
        # 累積帳戶價值
        df['Account_Market'] = initial_capital * (1 + df['Market_Return']).cumprod()
        df['Account_Strategy'] = initial_capital * (1 + df['Strategy_Return']).cumprod()
        
        # 結算數據
        total_trades = int(df['Trade'].sum())
        final_market = df['Account_Market'].dropna().iloc[-1]
        final_strategy = df['Account_Strategy'].dropna().iloc[-1]
        
        # 顯示看板
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("死抱著不賣 (餘額)", f"${final_market:,.0f}")
        m2.metric("均線策略 (餘額)", f"${final_strategy:,.0f}")
        m3.metric("策略勝出額", f"${(final_strategy - final_market):,.0f}")
        m4.metric("總交易次數", f"{total_trades} 次")
            
        # 繪製資金成長圖
        st.markdown("#### 📊 帳戶餘額成長對照 (含手續費/稅)")
        fig2, ax2 = plt.subplots(figsize=(14, 5))
        ax2.plot(df.index, df['Account_Market'], label='Buy & Hold', color='gray', alpha=0.6)
        ax2.plot(df.index, df['Account_Strategy'], label='Strategy', color='red', linewidth=2.5)
        ax2.axhline(initial_capital, color='black', linestyle='--', alpha=0.5)
        ax2.set_ylabel("Balance ($)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        st.pyplot(fig2)
