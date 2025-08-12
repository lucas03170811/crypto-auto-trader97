# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴 (輕量但包含常見 build 工具)
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    && apt-get clean

# 升級 pip 並安裝 numpy (相容版本)
RUN pip install --upgrade pip
RUN pip install numpy==1.24.4

# 先複製 requirements 並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案
COPY . .

# 在 COPY 後驗證檔案是否存在（build log 會列出）
RUN echo "===== /app tree =====" && ls -R /app || true \
 && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
 && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
