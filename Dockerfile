FROM python:3.11-slim

# 安裝必要系統套件（不含 TA-Lib 系統套件，改用 ta-lib-bin）
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
    && rm -rf /var/lib/apt/lists/*

# 更新 pip
RUN pip install --upgrade pip

# 設定工作目錄
WORKDIR /app

# 先安裝 requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 自動時間戳避免快取
RUN echo "CACHEBUST=$(date +%s)"

# 複製專案檔案
COPY . .

# 檢查 strategies 資料夾是否存在
RUN echo "===== /app tree =====" && ls -R /app || true \
    && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

# 啟動指令
CMD ["python", "main.py"]
