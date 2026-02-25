import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 網頁設定 ---
st.set_page_config(page_title="量化交易儀表板", layout="wide")
st.title("📈 專屬股票技術分析與真實本金回測")

# --- 快取函數：解決連線過於頻繁被擋的問題 ---
@st.cache_data(ttl=3600)  # 將抓下來的資料快取 1 小時
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 抓取 1 年資料確保均線計算完整
        data = ticker.history(period="1y")
        return data
    except Exception:
        return pd.DataFrame()

# --- 輸入區塊 ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    stock_id = st.text_input("請輸入股票代號 (例如: 2330.TW)", "2330.TW")
with col_b:
    initial_capital = st.number_input("請輸入初始本金", value=1000000, step=100000)
with col_c:
    cost_input = st.number_input("單次交易成本 (%)", value=0.20, step=0.05)
    cost_pct = cost_input / 100

st.markdown("### ⚙️ 請選擇要顯示的技術指標：")
col1, col2, col3, col4, col5 = st.columns(5)
with col1: show_5ma = st.checkbox("顯示 5MA", value=True)
with col2: show_10ma = st.checkbox("顯示 10MA", value=True)
with col3: show_20ma = st.checkbox("顯示 20MA", value=True)
with col4: show_60ma = st.checkbox("顯示 60MA", value=False)
with col5: show_bb = st.checkbox("顯示 布林通道", value=False)

if stock_id:
    # 使用快取函數抓取資料
    df = get_stock_data(stock_id)
    
    if df.empty:
        st.warning("目前暫時無法從 Yahoo 取得資料，請等候幾分鐘再重新整理網頁。")
    else:
        st.success(f"{stock_id} 資料讀取成功！")
        
        # 計算均線
        df['5MA']  = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        # 繪製上半部技術線圖
        fig, ax1 = plt.subplots(figsize=(14, 6))
        ax1.plot(df.index, df['Close'], label='Close Price', color='dodgerblue', alpha=0.8)
        if show_5ma: ax1.plot(df.index, df['5MA'], label='5MA', color='orange')
        if show_10ma: ax1.plot(df.index, df['10MA'], label='10MA', color='purple')
        if show_20ma: ax1.plot(df.index, df['20MA'], label='20MA', color='red')
        if show_60ma: ax1.plot(df.index, df['60MA'], label='60MA', color='green')
        ax1.set_title(f"{stock_id} Technical Analysis", fontsize=16)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        st.pyplot(fig)

        # --- 回測系統 (包含摩擦成本) ---
        st.markdown("---")
        st.markdown(f"### 💰 雙均線策略回測結果 (投入本金：{initial_capital:,} 元)")
        
        # 產生訊號與偵測交易
        df['Signal'] = np.where(df['5MA'] > df['20MA'], 1, 0)
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        
        # 計算報酬率
        df['Market_Return'] = df['Close'].pct_change()
        # 策略收益 = (昨日持有 * 今日漲跌) - (今日交易 * 摩擦成本)
        df['Strategy_Return'] = (df['Signal'].shift(1) * df['Market_Return']) - (df['Trade'] * cost_pct)
        
        # 累積資金成長
        df['Account_Market'] = initial_capital * (1 + df['Market_Return']).cumprod()
        df['Account_Strategy'] = initial_capital * (1 + df['Strategy_Return']).cumprod()
        
        # 結算數據
        final_market = df['Account_Market'].dropna().iloc[-1]
        final_strategy = df['Account_Strategy'].dropna().iloc[-1]
        total_trades = int(df['Trade'].sum())
        
        met1, met2, met3, met4 = st.columns(4)
        met1.metric("死抱著不賣 (餘額)", f"${final_market:,.0f}")
        met2.metric("均線策略 (餘額)", f"${final_strategy:,.0f}")
        met3.metric("總交易次數", f"{total_trades} 次")
        
        diff = final_strategy - final_market
        met4.metric("策略表現", f"${diff:,.0f}", delta=f"{diff:,.0f}")
            
        st.markdown("#### 📊 真實帳戶餘額走勢對比 (含摩擦成本)")
        fig2, ax2 = plt.subplots(figsize=(14, 5))
        ax2.plot(df.index, df['Account_Market'], label='Buy & Hold', color='gray', alpha=0.7)
        ax2.plot(df.index, df['Account_Strategy'], label='5MA/20MA Strategy', color='red', linewidth=2)
        ax2.axhline(initial_capital, color='black', linestyle='--', alpha=0.5)
        ax2.set_ylabel("Account Balance ($)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        # 格式化 Y 軸顯示千分位金額
        ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        st.pyplot(fig2)
