import sys
import os
from app_transaction import STORAGE_PATH, parse_block

def check_log(target_user=None):
    # 如果沒傳參數，就從命令列抓取 (sys.argv[1])
    if target_user is None:
        if len(sys.argv) < 2:
            print("用法: python3 app_checkLog.py [使用者名稱]")
            return []
        target_user = sys.argv[1]
    
    # 1. 取得所有區塊檔案並排序 (1.txt, 2.txt...)
    if not os.path.exists(STORAGE_PATH):
        print(f"錯誤: 找不到資料夾 {STORAGE_PATH}")
        return []

    files = [f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()]
    files.sort(key=lambda x: int(x[:-4]))

    print(f"--- 查詢使用者 '{target_user}' 的所有交易紀錄 ---")
    results = []
    found = False

    # 2. 逐一讀取區塊並過濾交易
    for file_name in files:
        file_path = os.path.join(STORAGE_PATH, file_name)
        data = parse_block(file_path)
        
        for tx in data["transactions"]:
            # 將交易紀錄切割成 [寄件人, 收件人, 金額] 並去除空白
            parts = [p for p in tx.split(",")]
            if len(parts) >= 2:
                sender = parts[0]
                receiver = parts[1]
                # 精確比對使用者名稱
                if target_user == sender or target_user == receiver:
                    line = f"[{file_name}] {tx}"
                    print(line)
                    results.append(line)
                    found = True

    if not found:
        print("查無此使用者的交易紀錄。")
    
    return results

if __name__ == "__main__":
    check_log()
