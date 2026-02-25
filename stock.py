import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 網頁設定 ---
st.set_page_config(page_title="量化交易儀表板", layout="wide")
st.title("📈 專屬股票技術分析與真實本金回測")

# --- 【新增】快取函數：避免被 Yahoo Finance 封鎖 ---
@st.cache_data(ttl=3600)  # 資料會保留 1 小時 (3600秒)，這期間重複輸入相同代號不需重新抓取
def get_stock_data(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="1y")

# --- 輸入區塊 ---
col_a, col_b, col_c = st.columns(3)
with col_a:
    stock_id = st.text_input("請輸入股票代號 (例如: 2330.TW)", "2330.TW")
with col_b:
    initial_capital = st.number_input("請輸入初始本金", value=1000000, step=100000)
with col_c:
    cost_input = st.number_input("單次交易成本 (%)", value=0.20, step=0.05)
    cost_pct = cost_input / 100

if stock_id:
    try:
        st.write(f"正在分析 **{stock_id}**...")
        # 改用我們寫的快取函數來抓資料
        df = get_stock_data(stock_id)
        
        if df.empty:
            st.error("找不到資料，請確認代號！")
        else:
            # --- 以下維持你原本的計算與畫圖邏輯 ---
            df['5MA']  = df['Close'].rolling(window=5).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            
            # (中間畫圖與回測程式碼省略，請保留你原本的版本內容)
            # ...
            
            st.success(f"{stock_id} 資料讀取成功！")
            
    except Exception as e:
        st.error(f"連線不穩定，請稍等幾秒後手動重新整理網頁。錯誤類型: {type(e).__name__}")
