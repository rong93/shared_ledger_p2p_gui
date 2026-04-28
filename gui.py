import streamlit as st
import os
import time
import socket
from p2p import P2PNode
from app_transaction import get_balances, STORAGE_PATH

# 設定頁面配置
st.set_page_config(page_title="P2P Shared Ledger", layout="wide")

# 1. 初始化 P2P 節點
@st.cache_resource
def get_node():
    # 這裡預設使用 8001 port (與 p2p.py 一致)
    my_port = 8001
    # 取得鄰居節點 (在 Docker 環境中通常是 client1, client2, client3)
    peer_list = [('client1', 8001), ('client2', 8001), ('client3', 8001)]
    
    node = P2PNode(my_port, peer_list)
    # 啟動監聽，但不進入 CLI 選單
    node.start(interactive=False)
    return node

node = get_node()

# --- 側邊欄：節點資訊 ---
st.sidebar.title("🛠 節點控制台")
st.sidebar.info(f"**目前主機:** {node.my_hostname}")
st.sidebar.info(f"**監聽埠號:** {node.port}")

# --- 側邊欄：餘額顯示 (垂直排列) ---
st.sidebar.divider()
st.sidebar.subheader("💰 帳戶餘額")
balances = get_balances()
if balances:
    for user, balance in balances.items():
        st.sidebar.metric(label=user, value=f"${balance}")
else:
    st.sidebar.warning("目前帳本中尚無使用者資料。")

# --- 主畫面 ---
st.title("🌐 P2P 共享帳本系統")

st.divider()

# --- 兩欄配置：交易與帳本 ---
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("💸 發起新交易")
    with st.form("tx_form"):
        sender = st.text_input("發送者 (Sender)")
        receiver = st.text_input("接收者 (Receiver)")
        amount = st.number_input("金額 (Amount)", min_value=1, value=10)
        
        submit_button = st.form_submit_button("送出交易")
        
        if submit_button:
            if sender and receiver:

                # 執行交易
                node.send_transaction(sender, receiver, amount)
                time.sleep(1)

                # 檢查使用者是否存在及餘額是否足夠
                balances = get_balances()
                if sender not in balances or balances[sender] < amount:
                    st.error(f"❌ 交易失敗：{sender} 餘額不足或帳號不存在")
                else:                   
                    st.success(f"✅ 交易已廣播: {sender} -> {receiver} (${amount})")
                time.sleep(1) # 等待寫入
                st.rerun()
            else:
                st.error("❌ 請填寫發送者與接收者名稱")

with right_col:
    st.subheader("📦 本地區塊內容")
    files = sorted([f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
    if files:
        selected_file = st.selectbox("選擇區塊檔案", files, index=len(files)-1)
        file_path = os.path.join(STORAGE_PATH, selected_file)
        with open(file_path, "r") as f:
            content = f.read()
        st.code(content, language="text")
    else:
        st.info("目前尚無區塊檔案。")

# --- 底部：功能按鈕 ---
st.divider()
st.subheader("⚙️ 系統管理")
c1, c2, c3 = st.columns(3)
if c1.button("🔍 執行全網共識檢查 (Check All)"):
    # 這裡可以呼叫 node.check_all_chains 邏輯 (需稍微調整 p2p.py 使其回傳結果)
    st.info("功能執行中，請查看後台 Log...")
    
if c2.button("🛠 執行全網帳本修復 (Repair)"):
    st.info("修復程序啟動中...")

if c3.button("🔄 重新整理畫面"):
    st.rerun()

# 定期更新 (Streamlit 不支援背景 push，這是一個簡單的自動重整機制)
# st.empty() 
# time.sleep(5)
# st.rerun()
