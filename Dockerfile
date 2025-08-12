FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential wget git && apt-get clean

# 升級 pip 並先安裝 numpy
RUN pip install --upgrade pip
RUN pip install numpy==1.24.4

# 先複製 requirements.txt 再安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 強制重新複製所有程式碼
COPY . .

# 列出檔案結構以確保 strategies/trend.py 存在
RUN echo "===== /app tree =====" && ls -R /app \
    && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

# 啟動時立即輸出 log（-u = 不緩衝）
CMD ["python", "-u", "main.py"]
