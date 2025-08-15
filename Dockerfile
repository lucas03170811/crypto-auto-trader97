# 使用 Python 3.11 slim 版本
FROM python:3.11-slim

# 安裝系統依賴（含 TA-Lib）
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    tar \
    libffi-dev \
    libssl-dev \
    python3-dev \
    gcc \
    make \
    libta-lib0 \
    libta-lib-dev \
    && rm -rf /var/lib/apt/lists/*

# 建立工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 加入時間戳破快取
ARG CACHEBUST=1
RUN echo "Cache bust at $(date)" > /cachebuster.txt

# 複製所有檔案
COPY . .

# 顯示 config.py 內容，確保是最新版本
RUN echo "===== [Docker DEBUG] config.py 內容 =====" && cat /app/config.py && echo "===================================="

# 執行主程式
CMD ["python", "main.py"]
