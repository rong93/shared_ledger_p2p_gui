# 分散式帳本專案自動化工具

.PHONY: init start stop clean restart help

# 預設顯示幫助訊息
help:
	@echo "使用方法:"
	@echo "  make init    - 1. 啟動容器 2. 初始化帳本 3. 同步至所有節點"
	@echo "  make start   - 僅啟動 Docker 容器"
	@echo "  make stop    - 停止並移除 Docker 容器"
	@echo "  make clean   - 停止容器並清空所有 client 的儲存資料"
	@echo "  make restart - 重新啟動所有服務"

# 核心初始化流程
init:
	@echo ">>> 正在啟動 Docker 容器..."
	docker compose up -d
	@echo ">>> 正在 client-1 執行帳本初始化 (app_init.py)..."
	docker exec -it client-1 python3 app_init.py
	@echo ">>> 同步初始帳本至 client-2 與 client-3..."
	@# 確保目錄存在並強制覆蓋
	rm -rf storage/client2/*
	cp -rf storage/client1/* storage/client2/
	rm -rf storage/client3/*
	cp -rf storage/client1/* storage/client3/
	sudo chmod -R 777 ./storage/
	@echo ">>> [成功] 所有節點初始化與同步完成！"

# 僅啟動
start:
	docker compose up -d

# 停止
stop:
	docker compose down

# 清理所有帳本紀錄
clean:
# 	docker compose down
	@echo ">>> 正在清空儲存目錄..."
	rm -rf storage/client1/*
	rm -rf storage/client2/*
	rm -rf storage/client3/*
	@# 保留 .gitkeep 避免目錄被刪除
	@touch storage/client1/.gitkeep storage/client2/.gitkeep storage/client3/.gitkeep
	@echo ">>> 已恢復乾淨狀態。"

# 重啟
restart: stop start
