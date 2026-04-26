import socket
import threading
import os
import sys
import time

# 匯入現有的功能模組邏輯
from app_transaction import process_transaction, get_balances, STORAGE_PATH, parse_block, get_file_hash
from app_checkChain import check_chain
from app_checkLog import check_log

# 每個 container 都要執行這份檔案
class P2PNode:
    def __init__(self, port, peers):
        self.port = port # 這台 container 的 port
        self.peers = peers # 這台 container 要傳給誰資料
        self.my_hostname = socket.gethostname() # 這台 container 的 名稱(ex: client-1)

        # 收集回應的暫存
        self.responses = []
        self.is_collecting = False

        # 使用 IPv4 格式 ，使用 UDP 協定 的 廣播機制

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 定義收件地址 寫 0.0.0.0 代表 會傳到 這台 container 的 外部和內部 IP 地址
        self.sock.bind(('0.0.0.0', self.port))

    # 按照 checkAllChains 需求所加入的功能
    def _get_last_block_hash(self):
        """取得本地端最後一個區塊的 Hash"""
        if not os.path.exists(STORAGE_PATH):
            return "None"
        # 抓取所有 .txt 檔案並排序
        files = [f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()]
        if not files:
            return "None"
        files.sort(key=lambda x: int(x[:-4]))
        
        # 取得最後一個檔案的路徑並計算其 Hash
        last_file_path = os.path.join(STORAGE_PATH, files[-1])
        return get_file_hash(last_file_path)

    def start(self):
        # 啟動背景監聽線程

        # 讓程式可以同時做兩件事。監聽外面的廣播 和 輸入指令的畫面。
        listener = threading.Thread(target=self._listen, daemon=True)
        listener.start()

        print(f"P2P 節點已啟動，監聽 Port: {self.port}")
        
        # 進入指令選單循環
        self._menu_loop()

    def _listen(self):
        """背景監聽：持續接收其他節點廣播的交易訊息"""
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode('utf-8')
                
                # 執行 checkAllChains 時，會接收到請求 要回傳最後一個 block 的 hash
                if msg == "CHECK_REQUEST":
                    last_hash = self._get_last_block_hash()
                    response = f"HASH_RES:{last_hash}"
                    self.sock.sendto(response.encode('utf-8'), addr)
                
                # 接收別人的 Hash 回報
                elif msg.startswith("HASH_RES:") and self.is_collecting:
                    res_hash = msg.split(":")[1]
                    self.responses.append((addr, res_hash))

                # 解析交易訊息 格式: "sender,receiver,amount"
                if "," in msg:
                    parts = msg.split(",")
                    if(parts[0] == "transaction"):
                        if len(parts) == 4:
                            sender, receiver, amount = parts[1], parts[2], int(parts[3])

                            print(f"\n[接收廣播] 已接收來自 {addr} 的交易: {sender} -> {receiver} ({amount})\n")
                            process_transaction(sender, receiver, amount)

                            print("=" * 64 +"\nEnter a command (checkMoney, checkLog, transaction, checkChain, checkAllChains): ", end="", flush=True)
            except Exception:
                pass

    def _broadcast(self, message):
           """廣播給所有人，但跳過自己"""
           for peer_host, peer_port in self.peers:
               # 如果鄰居的名稱跟我的容器名稱一樣，就跳過
               if peer_host == self.my_hostname:
                   continue
               try:
                   self.sock.sendto(message.encode('utf-8'), (peer_host, peer_port))
               except Exception as e:
                   print(f"發送至 {peer_host} 失敗: {e}")

    def _menu_loop(self):
        """主要互動式指令選單"""
        while True:
            user_input = input("=" * 64 +"\nEnter a command (checkMoney, checkLog, transaction, checkChain, checkAllChains): ").strip().split()
            if not user_input:
                continue
            
            cmd = user_input[0]

            if cmd == "transaction":
                if len(user_input) == 4:
                    sender, receiver, amount_str = user_input[1], user_input[2], user_input[3]
                    try:
                        amount = int(amount_str)


                        # 1. 廣播訊息給其他節點，讓全網同步
                        msg = f"{cmd},{sender},{receiver},{amount}"
                        self._broadcast(msg)

                        print(f"\n[發送廣播] {cmd}: {sender} -> {receiver} ({amount})\n")

                        # 2. 更新並記錄在自己的本地帳本
                        process_transaction(sender, receiver, amount)


                    except ValueError:
                        print("錯誤: 金額必須是數字。")
                else:
                    print("用法: transaction <Sender> <Receiver> <Amount>")

            elif cmd == "checkMoney":
                if len(user_input) == 2:
                    user = user_input[1]
                    balances = get_balances()
                    if user in balances:
                        print(f"{user} 的目前餘額為: {balances[user]}")
                    else:
                        print(f"找不到使用者 '{user}'")
                else:
                    print("用法: checkMoney <User>")

            elif cmd == "checkChain":
                if len(user_input) == 2:
                    reward_user = user_input[1]
                    if check_chain(reward_user): #檢查沒有錯誤的話 就需要 做到交易 所以要廣播

                        msg = f"transaction,Angel,{reward_user},10"
                        self._broadcast(msg)

                        print(f"\n[發送廣播] transaction: Angel -> {reward_user} (10)\n")

                else:
                    print("用法: checkChain <RewardUser>")

            elif cmd == "checkAllChains":
                if len(user_input) == 2:
                    reward_user = user_input[1]
                    
                    # 1. 自己先算 (Step 2: 本地自檢並取得最後 Hash)
                    my_hash = self._get_last_block_hash()
                    print(f"\n本地端最終指紋 (Sha256): {my_hash}")

                    # 2. 發起全網廣播
                    self.responses = []
                    self.is_collecting = True
                    self._broadcast("CHECK_REQUEST")
                    
                    # 3. 簡單等待：直到收齊所有鄰居的回應 (假設鄰居數量為 len(peers)-1)
                    expected_count = len(self.peers) - 1
                    print(f"正在等待其餘 {expected_count} 個節點回應並進行比對...")
                    
                    while len(self.responses) < expected_count:
                        time.sleep(0.1) 

                    self.is_collecting = False

                    # 4. 兩兩比對 (Step 1)
                    all_match = True
                    for addr, remote_hash in self.responses:
                        if remote_hash == my_hash:
                            print(f"-> 節點 {addr}: Yes (二者的Sha256一樣)")
                        else:
                            print(f"-> 節點 {addr}: No (不一致)")
                            all_match = False
                    
                    # 5. 驗證成功獎勵
                    if all_match:
                        print(f"\n驗證完成：全網帳本一致！發放 100 元獎勵給 {reward_user}。")
                        
                        # 1. 廣播獎勵訊息給其他節點
                        msg = f"transaction,Angel,{reward_user},100"
                        self._broadcast(msg)

                        # 2. 更新自己的帳本
                        process_transaction("Angel", reward_user, 100)
                    else:
                        print("\n驗證失敗：帳本不一致或節點回應不足，不發放獎勵。")
                else:
                    print("用法: checkAllChains <RewardUser>")

            elif cmd == "checkLog":
                if len(user_input) == 2:
                    target_user = user_input[1]
                    check_log(target_user)
                else:
                    print("用法: checkLog <User>")

            elif cmd == "exit":
                print("系統關閉中...")
                break
            else:
                print(f"未知指令: {cmd}")

if __name__ == '__main__':
    # 設定節點(node)資訊：
    # 這裡的 node 就是指 每個 container 

    # 這表示有人傳訊息過來會傳送到 8001 port 
    my_port = 8001 


    # 對應到 docker-compose.yml 中每個 container_name
    # 這表示 指定訊息要傳給 哪個client 和 port 多少
    peer_list = [('client1', 8001), ('client2', 8001), ('client3', 8001)]
    
    node = P2PNode(my_port, peer_list)
    node.start()
