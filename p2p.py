import socket
import threading
import os
import sys

# 匯入現有的功能模組邏輯
from app_transaction import process_transaction, get_balances, STORAGE_PATH, parse_block
from app_checkChain import check_chain
from app_checkLog import check_log

# 每個 container 都要執行這份檔案
class P2PNode:
    def __init__(self, port, peers):
        self.port = port # 這台 container 的 port
        self.peers = peers # 這台 container 要傳給誰資料
        self.my_hostname = socket.gethostname() # 這台 container 的 名稱(ex: client-1)

        # 使用 IPv4 格式 ，使用 UDP 協定 的 廣播機制
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 定義收件地址 寫 0.0.0.0 代表 會傳到 這台 container 的 外部和內部 IP 地址
        self.sock.bind(('0.0.0.0', self.port))

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
                # 解析交易訊息 格式: "sender,receiver,amount"
                if "," in msg:
                    parts = msg.split(",")
                    if(parts[0] == "transaction"):
                        if len(parts) == 4:
                            sender, receiver, amount = parts[1], parts[2], int(parts[3])

                            print(f"\n[接收廣播] 已接收來自 {addr} 的交易: {sender} -> {receiver} ({amount})\n")
                            process_transaction(sender, receiver, amount)

                            print("=" * 64 +"\nEnter a command (checkMoney, checkLog, transaction, checkChain): ", end="", flush=True)
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
            user_input = input("=" * 64 +"\nEnter a command (checkMoney, checkLog, transaction, checkChain): ").strip().split()
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
