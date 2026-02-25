import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="量化策略最佳化儀表板", layout="wide")
st.title("📈 量化策略最佳化與成本分析儀表板")

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
stock_id = st.sidebar.text_input("股票代號 (如: 2330.TW)", "2330.TW")
initial_capital = st.sidebar.number_input("初始投資本金", value=1000000, step=100000)
cost_input = st.sidebar.number_input("單次交易摩擦成本 (%)", value=0.20, step=0.05, help="包含手續費與證交稅")
cost_pct = cost_input / 100

st.sidebar.markdown("---")
st.sidebar.header("🚀 投資策略組合")
# 提供不同的均線策略選單
strategy_option = st.sidebar.selectbox(
    "請選擇均線交叉組合",
    ["5MA / 20MA (短線順勢)", "5MA / 10MA (極短線)", "20MA / 60MA (中長線波段)", "自定義短均線 / 長均線"]
)

# 根據選單定義參數
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
        st.warning("目前暫時無法取得資料。可能是代號輸入錯誤，或是 Yahoo 伺服器忙碌中，請稍候再試。")
    else:
        # 計算均線
        df['Short_MA'] = df['Close'].rolling(window=short_p).mean()
        df['Long_MA'] = df['Close'].rolling(window=long_p).mean()
        
        # --- 繪製技術線圖 ---
        st.markdown(f"### {stock_id} 技術線圖 ({short_p}MA / {long_p}MA)")
        fig, ax1 = plt.subplots(figsize=(14, 5))
        ax1.plot(df.index, df['Close'], label='收盤價', color='dodgerblue', alpha=0.5)
        ax1.plot(df.index, df['Short_MA'], label=f'{short_p}MA', color='orange', linewidth=1.5)
        ax1.plot(df.index, df['Long_MA'], label=f'{long_p}MA', color='red', linewidth=1.5)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.2)
        st.pyplot(fig)

        # --- 核心回測運算 ---
        # 1. 產生訊號 (短均 > 長均 = 持有 1, 否則為 0)
        df['Signal'] = np.where(df['Short_MA'] > df['Long_MA'], 1, 0)
        # 2. 偵測交易動作 (訊號變換當天 = 1)
        df['Trade'] = df['Signal'].diff().fillna(0).abs()
        
        # 3. 計算報酬率
        df['Market_Return'] = df['Close'].pct_change()
        
        # 策略報酬 (不計成本)
        df['Strategy_Return_No_Cost'] = df['Signal'].shift(1) * df['Market_Return']
        df['Cum_Strategy_No_Cost'] = (1 + df['Strategy_Return_No_Cost'].fillna(0)).cumprod()
        
        # 4. 計算摩擦成本 (以當下帳戶估值計算每次交易扣除額)
        # 累計成本 = (交易次數 * 成本率 * 初始本金) -> 簡化為基於本金的損耗觀察
        df['Accum_Cost'] = (df['Trade'] * cost_pct * initial_capital).cumsum()
        
        # 5. 真實帳戶價值 (本金 * 策略累積報酬 - 累計成本)
        df['Account_Strategy'] = (initial_capital * df['Cum_Strategy_No_Cost']) - df['Accum_Cost']
        df['Account_Market'] = initial_capital * (1 + df['Market_Return']).cumprod()
        
        # --- 數據結算看板 ---
        st.markdown("---")
        st.markdown(f"### 💰 策略回測結算 (組合：{strategy_option})")
        
        # 結算數據
        final_market = df['Account_Market'].dropna().iloc[-1]
        final_strategy = df['Account_Strategy'].dropna().iloc[-1]
        total_cost = df['Accum_Cost'].iloc[-1]
        total_trades = int(df['Trade'].sum())
        net_profit = final_strategy - initial_capital

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("策略期末總額", f"${final_strategy:,.0f}")
        c2.metric("死抱不放總額", f"${final_market:,.0f}")
        # 獨立列出手續費觀察
        c3.metric("累計摩擦成本", f"${total_cost:,.0f}", delta=f"交易 {total_trades} 次", delta_color="inverse")
        c4.metric("策略淨獲利", f"${net_profit:,.0f}", delta=f"{(net_profit/initial_capital)*100:.1f}%")

        # --- 資金成長曲線圖 ---
        st.markdown("#### 📊 真實資金成長對比 (含摩擦成本 vs 不計成本)")
        fig2, ax2 = plt.subplots(figsize=(14, 5))
        ax2.plot(df.index, df['Account_Market'], label='Buy & Hold (大盤)', color='gray', alpha=0.4)
        ax2.plot(df.index, df['Account_Strategy'], label='Strategy (扣除成本後)', color='red', linewidth=2.5)
        
        # 輔助線：如果不計成本的理想狀態
        df['Account_No_Cost'] = initial_capital * df['Cum_Strategy_No_Cost']
        ax2.plot(df.index, df['Account_No_Cost'], label='理想策略 (不計成本)', color='orange', linestyle='--', alpha=0.7)
        
        ax2.axhline(initial_capital, color='black', linestyle='-', alpha=0.3)
        ax2.set_ylabel("Account Balance ($)")
        ax2.legend()
        ax2.grid(True, alpha=0.2)
        ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        st.pyplot(fig2)

        st.info("💡 **觀察建議**：當紅色實線與橘色虛線距離愈遠，表示該策略的交易頻率過高，手續費正嚴重侵蝕你的利潤。")
