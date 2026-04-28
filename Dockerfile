# 1. 使用官方 Python 輕量版作為基礎
FROM python:3.9-slim

# 2. 設定容器內的工作目錄
WORKDIR /app

# 3. 安裝 Streamlit
RUN pip install streamlit

# 4. 預先建立好共享帳本的掛載點
RUN mkdir -p /share

# 5. 讓容器啟動後空轉
CMD ["tail", "-f", "/dev/null"]

# 在終端機顯示使用者、主機、路徑
ENV PS1 "\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "
