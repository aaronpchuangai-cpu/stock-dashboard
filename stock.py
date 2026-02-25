import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. 專業網頁風格設定 (Custom CSS) ---
st.set_page_config(page_title="Pro Quant Expert", layout="wide")

st.markdown("""
    <style>
    /* 全域背景色 */
    .main { background-color: #f0f2f6; }
    /* Metric 卡片美化 */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e1e4e8;
    }
    /* 調整標題字體 */
    h1, h2, h3 { color: #1e293b; font-family: 'Inter', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心計算函數 (快取與 RSI) ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1y")
        return data
    except: return pd.DataFrame()

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

# --- 3. 側邊欄控制面板 ---
with st.sidebar:
    st.header("⚙️ 終端設定")
    input_ids = st.text_input("標的池 (逗號分隔)", "NVDA, AAPL, 2330.TW, TSLA")
    stock_list = [s.strip().upper() for s in input_ids.split(",")]
    target_stock = st.selectbox("🎯 當前分析標的", stock_list)
    
    st.markdown("---")
    initial_capital = st.number_input("投資本金", value=1000000, step=100000)
    cost_pct = st.slider("摩擦成本 (%)", 0.0, 1.0, 0.2, 0.05) / 100
    
    st.markdown("---")
    st.header("🚀 策略配置")
    strategy_option = st.selectbox("均線組合", ["5/20 MA", "20/60 MA", "自定義"])
    if strategy_option == "5/20 MA": short_p, long_p = 5, 20
    elif strategy_option == "20/60 MA": short_p, long_p = 20, 60
    else:
        c1, c2 = st.columns(2)
        short_p = c1.number_input("短均", 1, 100, 10)
        long_p = c2.number_input("長均", 2, 200, 30)
    
    use_rsi = st.checkbox("啟用 RSI 避險濾網", value=True)
    rsi_limit = st.slider("RSI 進場上限", 50, 90, 70)

# --- 4. 數據運算引擎 ---
if target_stock:
    df = get_stock_data(target_stock)
    if not df.empty:
        df['Short_MA'] = df['Close'].rolling(window=short_p).mean()
        df['Long_MA'] = df['Close'].rolling(window=long_p).mean()
        df['RSI'] = calculate_rsi(df['Close'])
        
        # 訊號邏輯
        df['MA_Signal'] = np.where(df['Short_MA'] > df['Long_MA'], 1, 0)
        df['Signal'] = np.where((df['MA_Signal'] == 1) & (df['RSI'] < rsi_limit), 1, 0) if use_rsi else df['MA_Signal']
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        
        # 報酬與 MDD
        df['Market_Ret'] = df['Close'].pct_change()
        df['Strat_Ret'] = (df['Signal'].shift(1) * df['Market_Ret']) - (df['Trade'] * cost_pct)
        df['Acc_Strat'] = initial_capital * (1 + df['Strat_Ret'].fillna(0)).cumprod()
        df['Acc_Market'] = initial_capital * (1 + df['Market_Ret'].fillna(0)).cumprod()
        
        df['Peak'] = df['Acc_Strat'].cummax()
        df['DD'] = (df['Acc_Strat'] - df['Peak']) / df['Peak']
        
        # --- 5. 視覺化呈現 ---
        st.title(f"📊 {target_stock} 策略量化報告")
        
        # 頂部指標卡片
        final_val = df['Acc_Strat'].iloc[-1]
        roi = ((final_val / initial_capital) - 1) * 100
        mdd = df['DD'].min() * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最終資產", f"${final_val:,.0f}")
        c2.metric("累積報酬率", f"{roi:.2f}%", f"{roi - ((df['Acc_Market'].iloc[-1]/initial_capital-1)*100):.1f}% vs 大盤")
        c3.metric("最大回撤 (MDD)", f"{mdd:.1f}%", delta_color="inverse")
        c4.metric("交易次數", f"{int(df['Trade'].sum())} 次")

        st.markdown("---")
        t1, t2 = st.tabs(["📈 趨勢與指標", "🛡️ 風險與資金"])

        with t1:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios':[3, 1]}, facecolor='#f8f9fa')
            # 價格圖
            ax1.plot(df.index, df['Close'], color='#bdc3c7', alpha=0.4, label='Price')
            ax1.plot(df.index, df['Short_MA'], color='#f39c12', linewidth=2, label=f'{short_p}MA')
            ax1.plot(df.index, df['Long_MA'], color='#e74c3c', linewidth=2, label=f'{long_p}MA')
            ax1.fill_between(df.index, df['Short_MA'], df['Long_MA'], where=(df['Short_MA'] >= df['Long_MA']), color='#2ecc71', alpha=0.1)
            ax1.set_facecolor('#ffffff')
            ax1.grid(True, linestyle='--', alpha=0.3)
            ax1.legend(frameon=False)
            # RSI 圖
            ax2.plot(df.index, df['RSI'], color='#9b59b6', linewidth=1.5)
            ax2.axhline(rsi_limit, color='#e74c3c', linestyle='--')
            ax2.axhline(30, color='#2ecc71', linestyle='--')
            ax2.fill_between(df.index, rsi_limit, 100, color='#e74c3c', alpha=0.05)
            ax2.set_ylim(0, 100)
            ax2.set_facecolor('#ffffff')
            st.pyplot(fig)

        with t2:
            fig2, (ax3, ax4) = plt.subplots(2, 1, figsize=(15, 8), gridspec_kw={'height_ratios':[2, 1]}, facecolor='#f8f9fa')
            # 資金圖
            ax3.plot(df.index, df['Acc_Market'], label='Market', color='#95a5a6', linestyle='--')
            ax3.plot(df.index, df['Acc_Strat'], label='Strategy', color='#2980b9', linewidth=2.5)
            ax3.set_facecolor('#ffffff')
            ax3.legend()
            # 回撤圖
            ax4.fill_between(df.index, df['DD']*100, 0, color='#e74c3c', alpha=0.2)
            ax4.plot(df.index, df['DD']*100, color='#c0392b', linewidth=1)
            ax4.set_ylabel("DD %")
            ax4.set_facecolor('#ffffff')
            st.pyplot(fig2)

        st.info(f"💡 **即時策略狀態**：{'🟢 持有中' if df['Signal'].iloc[-1] == 1 else '⚪ 空手中'} | RSI: {df['RSI'].iloc[-1]:.1f}")