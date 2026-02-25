import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 網頁設定 ---
st.set_page_config(page_title="量化交易儀表板", layout="wide")
st.title("📈 專屬股票技術分析與真實本金回測 (含交易成本)")

# --- 輸入區塊 ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    stock_id = st.text_input("請輸入股票代號 (例如: 2330.TW)", "2330.TW")
with col_b:
    initial_capital = st.number_input("請輸入初始本金", value=1000000, step=100000)
with col_c:
    # 新增：讓你可以自由調整單次交易成本
    cost_input = st.number_input("單次交易成本 (%)", value=0.20, step=0.05)
    cost_pct = cost_input / 100  # 轉換成小數點

st.markdown("### ⚙️ 請選擇要顯示的技術指標：")
col1, col2, col3, col4, col5 = st.columns(5)
with col1: show_5ma = st.checkbox("顯示 5MA", value=True)
with col2: show_10ma = st.checkbox("顯示 10MA", value=False)
with col3: show_20ma = st.checkbox("顯示 20MA", value=True)
with col4: show_60ma = st.checkbox("顯示 60MA", value=False)
with col5: show_bb = st.checkbox("顯示 布林通道", value=False)

if stock_id:
    st.write(f"正在抓取 **{stock_id}** 近一年的資料，並進行策略回測...")
    df = yf.Ticker(stock_id).history(period="1y")
    
    if df.empty:
        st.error("找不到資料，請確認代號！")
    else:
        df['5MA']  = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        # 繪製上半部技術線圖
        fig, ax1 = plt.subplots(figsize=(14, 6))
        ax1.plot(df.index, df['Close'], label='Close', color='dodgerblue', alpha=0.8)
        if show_5ma: ax1.plot(df.index, df['5MA'], label='5MA', color='orange')
        if show_10ma: ax1.plot(df.index, df['10MA'], label='10MA', color='purple')
        if show_20ma: ax1.plot(df.index, df['20MA'], label='20MA', color='red')
        if show_60ma: ax1.plot(df.index, df['60MA'], label='60MA', color='green')
        ax1.set_title(f"{stock_id} Technical Analysis")
        ax1.legend(loc='upper left')
        ax1.grid(True)
        st.pyplot(fig)

        # ==========================================
        # 🚀 核心回測系統：包含摩擦成本
        # ==========================================
        st.markdown("---")
        st.markdown(f"### 💰 雙均線策略回測結果 (投入本金：{initial_capital:,} 元)")
        
        # 1. 產生訊號 (1: 持有, 0: 空手)
        df['Signal'] = np.where(df['5MA'] > df['20MA'], 1, 0)
        
        # 2. 抓出「交易動作」！如果今天的訊號跟昨天不一樣，代表有買或賣 (數值變為 1)
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        
        # 3. 計算大盤每天的真實漲跌幅
        df['Market_Return'] = df['Close'].pct_change()
        
        # 4. 計算策略的報酬率 (超關鍵：扣除手續費)
        # 今天的獲利 = (昨天的狀態 * 今天的漲跌) - (今天是否有交易 * 交易成本)
        df['Strategy_Return'] = (df['Signal'].shift(1) * df['Market_Return']) - (df['Trade'] * cost_pct)
        
        # 5. 計算累積資金乘數與真實金額
        df['Cum_Market'] = (1 + df['Market_Return']).cumprod()
        df['Cum_Strategy'] = (1 + df['Strategy_Return']).cumprod()
        
        df['Account_Market'] = initial_capital * df['Cum_Market']
        df['Account_Strategy'] = initial_capital * df['Cum_Strategy']
        
        # 算一下總共交易了幾次
        total_trades = int(df['Trade'].sum())
        
        final_market = df['Account_Market'].dropna().iloc[-1]
        final_strategy = df['Account_Strategy'].dropna().iloc[-1]
        
        met1, met2, met3, met4 = st.columns(4)
        met1.metric("死抱著不賣 (期末餘額)", f"${final_market:,.0f}")
        met2.metric("均線策略 (期末餘額)", f"${final_strategy:,.0f}")
        
        diff_amount = final_strategy - final_market
        if diff_amount > 0:
            met3.metric("策略表現", "打敗大盤！🏆", f"+${diff_amount:,.0f}")
        else:
            met3.metric("策略表現", "輸給大盤 📉", f"${diff_amount:,.0f}")
            
        met4.metric("總交易次數 (買+賣)", f"{total_trades} 次")
            
        st.markdown("#### 📊 真實帳戶餘額走勢對比 (含摩擦成本)")
        fig2, ax2 = plt.subplots(figsize=(14, 5))
        ax2.plot(df.index, df['Account_Market'], label='Buy & Hold', color='gray', alpha=0.7)
        ax2.plot(df.index, df['Account_Strategy'], label='5MA/20MA Strategy', color='red', linewidth=2)
        ax2.axhline(initial_capital, color='black', linestyle='--', alpha=0.5)
        ax2.set_ylabel("Account Balance ($)")
        ax2.legend(loc='upper left')
        ax2.grid(True)
        ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        st.pyplot(fig2)