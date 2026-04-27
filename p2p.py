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

        self.responses = []
        self.is_waiting_other_clients_reply = False

        # 使用 IPv4 格式 ，使用 UDP 協定 的 廣播機制
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 定義收件地址 寫 0.0.0.0 代表 會傳到 這台 container 的 外部和內部 IP 地址
        self.sock.bind(('0.0.0.0', self.port))

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
                
                # 執行 checkAllChains 時，這裡 "其他 clients" 會回傳指定 index.txt 的 hash 值
                if msg.startswith("REQUEST_HASH_AT:"):
                    index = msg.split(":")[1]
                    target_file = os.path.join(STORAGE_PATH, f"{index}.txt")
                    res_hash = get_file_hash(target_file) if os.path.exists(target_file) else "None"
                    self.sock.sendto(f"RESPONSE_HASH_AT:{index}:{res_hash}".encode('utf-8'), addr)
                
                # 執行 checkAllChains 時，這裡 "主 client" 會接收別人回傳的 hash 值
                elif msg.startswith("RESPONSE_HASH_AT:") and self.is_waiting_other_clients_reply:
                    # 格式: RESPONSE_HASH_AT:index:hash
                    parts = msg.split(":")
                    index, res_hash = parts[1], parts[2]
                    self.responses.append((addr, index, res_hash))

                # 執行repairAllChains 時，處理檔案索取 (當別人跟我要正確帳本時)
                elif msg.startswith("REQUEST_FILE_AT:"):
                    idx_req = msg.split(":")[1]
                    file_path = os.path.join(STORAGE_PATH, f"{idx_req}.txt")
                    if os.path.exists(file_path):
                        with open(file_path, "r") as f:
                            content = f.read()
                        # 回傳格式: RESPONSE_FILE_AT:編號:內容
                        self.sock.sendto(f"RESPONSE_FILE_AT:{idx_req}:{content}".encode('utf-8'), addr)

                # 執行repairAllChains 時，處理檔案回傳 (當我收到別人給我的正確帳本時)
                elif msg.startswith("RESPONSE_FILE_AT:"):
                    file_parts = msg.split(":", 2) # header, idx, content
                    if len(file_parts) == 3:
                        idx_res, content = file_parts[1], file_parts[2]
                        file_path = os.path.join(STORAGE_PATH, f"{idx_res}.txt")
                        with open(file_path, "w") as f:
                            f.write(content)
                        print(f"  [修復通知] 第 {idx_res} 塊檔案已由遠端節點同步並覆寫成功。")

                # 解析交易訊息 格式: "sender,receiver,amount"
                if "," in msg:
                    parts = msg.split(",")
                    if(parts[0] == "transaction"):
                        if len(parts) == 4:
                            sender, receiver, amount = parts[1], parts[2], int(parts[3])

                            print(f"\n[接收廣播] 已接收來自 {addr} 的交易: {sender} -> {receiver} ({amount})\n")
                            process_transaction(sender, receiver, amount)

                            print("=" * 64 +"\nEnter a command (checkMoney, checkLog, transaction, checkChain, checkAllChains, repairAllChains): ", end="", flush=True)
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
            user_input = input("=" * 64 +"\nEnter a command (checkMoney, checkLog, transaction, checkChain, checkAllChains, repairAllChains): ").strip().split()
            if not user_input:
                continue
            
            cmd = user_input[0]

            if cmd == "transaction":
                if len(user_input) == 4:
                    sender,receiver, amount_str = user_input[1], user_input[2], user_input[3]
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
                    
                    # 取得本地所有區塊列表
                    files = sorted([f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
                    total_blocks = len(files)
                    
                    if total_blocks == 0:
                        print("尚無區塊可驗證。")
                        continue

                    # --- Step 1: 跨節點檢查最後一個區塊 ---
                    print(f"\n[Step 1] 跨節點檢查最後一個區塊 (第 {total_blocks} 塊)...")
                    self.responses = []
                    self.is_waiting_other_clients_reply = True
                    self._broadcast(f"REQUEST_HASH_AT:{total_blocks}")
                    
                    # 等待其餘節點回應 (假設鄰居數量為 len(peers)-1)
                    expected_count = len(self.peers) - 1
                    wait_start = time.time()
                    while len(self.responses) < expected_count and (time.time() - wait_start < 2.0):
                        time.sleep(0.1)
                    
                    self.is_waiting_other_clients_reply = False

                    # 判斷 Step 1 是否全數通過
                    my_last_hash = get_file_hash(os.path.join(STORAGE_PATH, f"{total_blocks}.txt"))
                    # 收到任一個節點的回傳結果後馬上進行兩兩比對，並輸出到螢幕
                    step1_match = True
                    for addr, res_idx, res_hash in self.responses:
                        if res_hash == my_last_hash:
                            print(f"  -> 節點 {addr}: Yes (二者的Sha256一樣)")
                        else:
                            print(f"  -> 節點 {addr}: No (不一致)")
                            step1_match = False
                    
                    if not step1_match or len(self.responses) < expected_count:
                        print("\n[Step 1 失敗] 最終區塊不一致或回應節點不足，驗證終止。")
                        continue

                    # --- Step 2: 從第一個區塊走到最後一個區塊，檢查所有本地端帳本 ---
                    print(f"\n[Step 2] 最後區塊一致，開始從頭逐塊檢查...")
                    all_chain_match = True
                    for i in range(1, total_blocks + 1):
                        print(f"正在驗證第 {i} 塊...")
                        self.responses = []
                        self.is_waiting_other_clients_reply = True
                        self._broadcast(f"REQUEST_HASH_AT:{i}")
                        
                        wait_start = time.time()
                        while len(self.responses) < expected_count and (time.time() - wait_start < 2.0):
                            time.sleep(0.1) 
                        
                        self.is_waiting_other_clients_reply = False

                        # 檢查這一輪的所有回應是否都正確
                        my_idx_hash = get_file_hash(os.path.join(STORAGE_PATH, f"{i}.txt"))
                        match_this_block = True
                        for addr, res_idx, res_hash in self.responses:
                            if res_hash == my_idx_hash:
                                print(f"  -> 節點 {addr}: Yes (二者的Sha256一樣)")
                            else:
                                print(f"  -> 節點 {addr}: No (不一致)")
                                match_this_block = False
                                all_chain_match = False
                        
                        if not match_this_block or len(self.responses) < expected_count:
                            print(f"\n[警告] 第 {i} 塊發現共識分歧或節點回應不足，驗證終止。")
                            all_chain_match = False
                            break
                    
                    # 5. 最終獎勵判斷
                    if all_chain_match:
                        print(f"\n驗證完成：全域帳本一致！發放 100 元獎勵給 {reward_user}。")
                        
                        # 1. 廣播獎勵訊息給其他節點
                        msg = f"transaction,Angel,{reward_user},100"
                        self._broadcast(msg)

                        # 2. 更新自己的帳本
                        process_transaction("Angel", reward_user, 100)
                    else:
                        print("\n驗證失敗：帳本存在分歧，不發放獎勵。")
                else:
                    print("用法: checkAllChains <RewardUser>")

            elif cmd == "repairAllChains":
                # 取得本地所有區塊列表
                files = sorted([f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()], key=lambda x: int(x[:-4]))
                total_blocks = len(files)
                
                print(f"\n開始執行全域帳本修復 (多數決)，總計區塊數: {total_blocks}")
                
                for i in range(1, total_blocks + 1):
                    print(f"--- 正在檢查第 {i} 塊 ---")
                    my_hash = get_file_hash(os.path.join(STORAGE_PATH, f"{i}.txt"))
                    
                    # 1. 廣播請求 Hash
                    self.responses = []
                    self.is_waiting_other_clients_reply = True
                    self._broadcast(f"REQUEST_HASH_AT:{i}")
                    
                    # 2. 等待回應
                    expected_count = len(self.peers) - 1
                    wait_start = time.time()
                    while len(self.responses) < expected_count and (time.time() - wait_start < 2.0):
                        time.sleep(0.1)
                    self.is_waiting_other_clients_reply = False

                    # 3. 統計投票 (包含自己)
                    all_votes = {my_hash: [("Local", my_hash)]}
                    for addr, res_idx, res_hash in self.responses:
                        if res_hash not in all_votes: all_votes[res_hash] = []
                        all_votes[res_hash].append((addr, res_hash))
                    
                    # 4. 尋找多數真相 (>50%)
                    total_nodes = len(self.peers)
                    truth_hash = None
                    for h, voters in all_votes.items():
                        if len(voters) > total_nodes / 2: # 多數決
                            truth_hash = h
                            break
                    
                    if truth_hash:
                        # 5. 首先確保「自己」是正確的
                        if my_hash != truth_hash:
                            valid_peers = [v[0] for v in all_votes[truth_hash] if v[0] != "Local"]
                            if valid_peers:
                                voter_addr = valid_peers[0]
                                print(f"  [本地異常] 正在向 {voter_addr} 索取正確檔案...")
                                self.sock.sendto(f"REQUEST_FILE_AT:{i}".encode('utf-8'), voter_addr)
                                time.sleep(0.6) # 等待背景寫入檔案
                        
                        # 6. 現在我已確保是正確的了，主動去修復那些「錯誤的鄰居」
                        # 讀取目前正確的內容
                        with open(os.path.join(STORAGE_PATH, f"{i}.txt"), "r") as f:
                            correct_content = f.read()
                            
                        for addr, res_idx, res_hash in self.responses:
                            if res_hash != truth_hash:
                                print(f"  [全域修復] 偵測到節點 {addr} 資料錯誤，正在推播正確檔案...")
                                self.sock.sendto(f"RESPONSE_FILE_AT:{i}:{correct_content}".encode('utf-8'), addr)
                        
                        if my_hash == truth_hash:
                            print(f"  [狀態正常] 本地與多數共識一致")
                    else:
                        print("➔ [嚴重錯誤] 找不到 >50% 的共識帳本，系統不被信任！")
                        break
                print("\n全域修復程序結束。")

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
