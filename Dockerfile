FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    && apt-get clean

# 更新 pip 並安裝 numpy (避免 ta-lib 編譯問題)
RUN pip install --upgrade pip
RUN pip install numpy==1.24.4

# 先複製 requirements 並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 加入隨機值破壞快取
ARG CACHE_BUSTER=1
ENV CACHE_BUSTER=${CACHE_BUSTER}

# 再複製完整專案
COPY . .

# 檢查 trend.py 是否存在
RUN echo "===== /app tree =====" && ls -R /app || true \
    && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

CMD ["python", "main.py"]
