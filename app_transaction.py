import os
import hashlib
import sys
import json

# 設定區塊限制與路徑
STORAGE_PATH = "./storage"
BLOCK_CAPACITY = 5
INIT_FILE = f"{STORAGE_PATH}/init.json"

def get_balances():
    """從 init.json 讀取所有餘額"""
    if os.path.exists(INIT_FILE):
        with open(INIT_FILE, "r") as f:
            return json.load(f)
    return {}

def update_balances(balances):
    """將餘額寫回 init.json"""
    with open(INIT_FILE, "w") as f:
        json.dump(balances, f, indent=4)

def get_file_hash(file_path):
    """計算檔案內容的 SHA256"""
    if not os.path.exists(file_path):
        return "None"
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def parse_block(file_path):
    """解析自定義 .txt 格式"""
    data = {"prev_hash": "None", "next_block": "None", "transactions": []}
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            line1 = f.readline()
            line2 = f.readline()
            if line1: data["prev_hash"] = line1.split(":")[-1].strip()
            if line2: data["next_block"] = line2.split(":")[-1].strip()
            data["transactions"] = [line.strip() for line in f if line.strip()]
    return data

def write_block(file_path, data):
    """寫回自定義 .txt 格式"""
    with open(file_path, "w") as f:
        f.write(f"Sha256 of previous block:{data['prev_hash']}\n")
        f.write(f"Next block:{data['next_block']}\n")
        for tx in data["transactions"]:
            f.write(f"{tx}\n")

def get_target_block():
    """根據資料夾狀態決定寫入目標：永遠優先寫入倒數第二個，除非它滿了"""
    if not os.path.exists(STORAGE_PATH):
        os.makedirs(STORAGE_PATH)
    
    files = [f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()]
    if not files:
        return 1
    
    max_num = sorted([int(f[:-4]) for f in files])[-1]
    
    if max_num == 1:
        # 如果只有 1.txt，檢查它滿了沒
        data = parse_block(f"{STORAGE_PATH}/1.txt")
        return 1 if len(data["transactions"]) < BLOCK_CAPACITY else 2
    
    # 如果有 N.txt (N > 1)，檢查 (N-1).txt 滿了沒
    prev_num = max_num - 1
    prev_data = parse_block(f"{STORAGE_PATH}/{prev_num}.txt")
    
    if len(prev_data["transactions"]) < BLOCK_CAPACITY:
        return prev_num # 倒數第二個還沒滿
    else:
        return max_num  # 倒數第二個滿了，寫入目前最後一個

def process_transaction(sender, receiver, amount):
    # 1. 餘額處理
    balances = get_balances()
    if sender not in balances: balances[sender] = 0
    if receiver not in balances: balances[receiver] = 0
    if balances[sender] < amount:
        print(f"轉帳失敗: {sender} 餘額不足")
        update_balances(balances)
        return False

    balances[sender] -= amount
    balances[receiver] += amount
    update_balances(balances)

    # 2. 決定寫入目標
    current_num = get_target_block()
    file_path = f"{STORAGE_PATH}/{current_num}.txt"
    data = parse_block(file_path)

    # 補上雜湊鏈結
    if data["prev_hash"] == "None":
        if current_num == 1:
            data["prev_hash"] = "0" * 64
        else:
            data["prev_hash"] = get_file_hash(f"{STORAGE_PATH}/{current_num - 1}.txt")

    # 3. 寫入新交易並設定指標
    data["transactions"].append(f"{sender},{receiver},{amount}")
    next_num = current_num + 1
    data["next_block"] = f"{next_num}.txt"
    write_block(file_path, data)

    # 4. 更新下一個區塊的雜湊
    current_hash = get_file_hash(file_path)
    next_file_path = f"{STORAGE_PATH}/{next_num}.txt"
    next_data = parse_block(next_file_path)
    next_data["prev_hash"] = current_hash
    write_block(next_file_path, next_data)

    print(f"交易已寫入 {current_num}.txt ({len(data['transactions'])}/{BLOCK_CAPACITY})")
    return True

def transaction():
    if len(sys.argv) != 4:
        print("用法: python3 app_transaction.py [寄件人] [收件人] [金額]")
        return
    sender, receiver, amount = sys.argv[1], sys.argv[2], int(sys.argv[3])
    process_transaction(sender, receiver, amount)

if __name__ == "__main__":
    transaction()
