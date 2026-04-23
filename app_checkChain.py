import sys
import os
from app_transaction import STORAGE_PATH, get_file_hash, parse_block, process_transaction

def check_chain(reward_user=None):
    # 如果沒從函數傳入參數，則嘗試從命令列參數抓取 (sys.argv[1])
    if reward_user is None:
        if len(sys.argv) < 2:
            print("用法: python3 app_checkChain.py [獎勵領取者]")
            return False
        reward_user = sys.argv[1]

    # 1. 取得並排序所有區塊
    if not os.path.exists(STORAGE_PATH):
        print("錯誤: 找不到資料夾")
        return False

    files = [f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()]
    files.sort(key=lambda x: int(x[:-4]))

    if len(files) < 1:
        print("尚無區塊")
        return False

    # 2. 逐一比對 Hash 鍊
    for i in range(len(files) - 1):
        curr_file = files[i]
        next_file = files[i+1]

        curr_path = os.path.join(STORAGE_PATH, curr_file)
        next_path = os.path.join(STORAGE_PATH, next_file)

        actual_hash = get_file_hash(curr_path)
        next_data = parse_block(next_path)
        recorded_hash = next_data["prev_hash"]

        if actual_hash != recorded_hash:
            print(f"帳本鍊受損，錯誤的區塊編號: {curr_file}")
            return False

    # 3. 檢查通過，發放獎勵
    print("OK 檢查通過")
    
    # 呼叫 process_transaction 確保獎勵也會記錄在帳本中
    if process_transaction("Angel", reward_user, 10):
        print(f"驗證完成！ Angel 已支付 10 元獎勵給 {reward_user} 並記錄在帳本中。")
    else:
        print("驗證完成，但 Angel 餘額不足以支付獎金。")

    return True

if __name__ == "__main__":
    check_chain()
