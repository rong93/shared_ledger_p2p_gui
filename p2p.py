import socket
import threading
import os
import sys

# 匯入現有的功能模組邏輯
from app_transaction import process_transaction, get_balances, STORAGE_PATH, parse_block
from app_checkChain import check_chain as run_check_chain

# 每個 container 都要執行這份檔案
class P2PNode:
    def __init__(self, port, peers):
        self.port = port
        self.peers = peers
        # 使用 UDP 協定，符合 requirement.md 描述的廣播機制
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 綁定 0.0.0.0 以接收所有網路介面的訊息
        self.sock.bind(('0.0.0.0', self.port))

    def start(self):
        # 啟動背景監聽線程
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
                    if len(parts) == 3:
                        sender, receiver, amount = parts[0], parts[1], int(parts[2])
                        # 自動寫入本地帳本
                        process_transaction(sender, receiver, amount)
                        print(f"\n[網路同步] 已接收並記錄來自 {addr} 的交易: {sender} 轉帳 {amount} 給 {receiver}")
                        print("Enter a command (checkMoney, checkLog, transaction, checkChain): ", end="", flush=True)
            except Exception:
                pass

    def _broadcast(self, message):
        """將交易訊息廣播給所有已知節點"""
        for peer in self.peers:
            try:
                self.sock.sendto(message.encode('utf-8'), peer)
            except:
                pass

    def _menu_loop(self):
        """主要互動式指令選單"""
        while True:
            cmd = input("\nEnter a command (checkMoney, checkLog, transaction, checkChain): ").strip()

            if cmd == "transaction":
                sender = input("Sender: ").strip()
                receiver = input("Receiver: ").strip()
                try:
                    amount = int(input("Amount: "))
                    # 1. 先更新並記錄在自己的本地帳本
                    if process_transaction(sender, receiver, amount):
                        # 2. 廣播訊息給其他節點，讓全網同步
                        msg = f"{sender},{receiver},{amount}"
                        self._broadcast(msg)
                        print("交易成功並已廣播至 P2P 網路。")
                except ValueError:
                    print("錯誤: 金額必須是數字。")

            elif cmd == "checkMoney":
                user = input("User name: ").strip()
                balances = get_balances()
                if user in balances:
                    print(f"{user} 的目前餘額為: {balances[user]}")
                else:
                    print(f"找不到使用者 '{user}'")

            elif cmd == "checkChain":
                reward_user = input("Who gets the reward? ").strip()
                # 模擬 sys.argv 以調用 app_checkChain.py 的邏輯
                sys.argv = ["app_checkChain.py", reward_user]
                run_check_chain()

            elif cmd == "checkLog":
                target_user = input("要查詢哪位使用者的交易紀錄: ").strip()
                self._show_logs(target_user)

            elif cmd == "exit":
                print("系統關閉中...")
                break
            elif not cmd:
                continue
            else:
                print(f"未知指令: {cmd}")

    def _show_logs(self, target_user):
        """顯示指定使用者的所有交易日誌 (對應 app_checkLog.py 功能)"""
        if not os.path.exists(STORAGE_PATH):
            print("目前尚無帳本紀錄。")
            return
        
        files = [f for f in os.listdir(STORAGE_PATH) if f.endswith(".txt") and f[:-4].isdigit()]
        files.sort(key=lambda x: int(x[:-4]))
        
        print(f"--- {target_user} 的交易紀錄 ---")
        found = False
        for file_name in files:
            data = parse_block(os.path.join(STORAGE_PATH, file_name))
            for tx in data["transactions"]:
                if target_user in tx:
                    print(f"[{file_name}] {tx}")
                    found = True
        if not found:
            print("查無此使用者的交易紀錄。")

if __name__ == '__main__':
    # 設定節點資訊：
    # 在 Docker 網路中，node1, node2, node3 會自動解析為對應容器的 IP
    my_port = 8001
    peer_list = [('node1', 8001), ('node2', 8001), ('node3', 8001)]
    
    node = P2PNode(my_port, peer_list)
    node.start()
