import os
import shutil
import random
import json
from app_transaction import process_transaction, STORAGE_PATH, INIT_FILE

def reset_and_simulate():
    # 1. 快速清空 storage 資料夾內容 (保留資料夾本身)
    if os.path.exists(STORAGE_PATH):
        os.system(f"rm -rf {STORAGE_PATH}/*")
    else:
        os.makedirs(STORAGE_PATH)
    print(f"已清空 {STORAGE_PATH} 資料夾內容。")

    # 2. 建立初始餘額 init.json
    initial_balances = {
        "Angel": 1000000,
        "A": 10000,
        "B": 10000,
        "C": 10000,
        "D": 10000,
        "E": 10000
    }
    with open(INIT_FILE, "w") as f:
        json.dump(initial_balances, f, indent=4)
    print("已重置 init.json 初始金額。")

    # 3. 準備模擬資料
    users = ["A", "B", "C", "D", "E"]
    num_transactions = 100

    print(f"正在產生 {num_transactions} 筆隨機交易...")
    
    for i in range(num_transactions):
        # 隨機挑選寄件人與收件人 (不能是同一人)
        sender, receiver = random.sample(users, 2)
        # 隨機金額 1~50
        amount = random.randint(1, 50)
        
        # 呼叫現有的交易邏輯
        process_transaction(sender, receiver, amount)

    print(f"\n模擬完成！已產生 {num_transactions} 筆交易，共計 {num_transactions // 5} 個區塊。")

if __name__ == "__main__":
    reset_and_simulate()
