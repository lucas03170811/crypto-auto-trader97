FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    wget \
    git \
    && apt-get clean

# 升級 pip
RUN pip install --upgrade pip

# 安裝依賴
COPY requirements.txt .
RUN pip install -r requirements.txt

# ✅ 驗證 pandas_ta 是否安裝成功
RUN python -c "import pandas_ta; print('[CHECK] pandas_ta installed successfully')"

# 複製程式碼
COPY . .

# 顯示重要檔案，方便除錯
RUN echo "=== strategies dir ===" && ls -l strategies/ || true
RUN echo "=== strategies dir ===" && ls -l strategies/ || true
RUN echo "=== binance_client.py ===" && cat exchange/binance_client.py

ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
