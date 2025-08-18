# 使用輕量級 Python 基底
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝必要的系統依賴（只保留最基本的編譯環境，pandas_ta 不需要 TA-Lib）
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝依賴
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製專案檔案
COPY . .

# 預設啟動指令
CMD ["python", "main.py"]
