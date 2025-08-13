FROM python:3.11-slim

# 安裝必要系統套件
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    && apt-get clean

# 更新 pip 並安裝 numpy 版本
RUN pip install --upgrade pip
RUN pip install numpy==1.24.4

# 設定工作目錄
WORKDIR /app

# 先安裝套件需求
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 用時間戳記強制跳過 cache，確保 COPY . . 每次都更新
ARG CACHEBUST
RUN echo "CACHEBUST value: ${CACHEBUST}"

# 複製全部專案檔案
COPY . .

# 檢查 trend.py 是否存在
RUN echo "===== /app tree =====" && ls -R /app || true \
    && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

# 設定啟動指令
CMD ["python", "main.py"]
