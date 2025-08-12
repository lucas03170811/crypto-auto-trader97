FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y gcc g++ make

# 複製需求檔
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 部署時檢查 strategies 資料夾與 trend.py 是否存在
RUN mkdir -p /app/strategies \
    && echo "[DEBUG] Listing /app after pip install:" \
    && ls -l /app \
    && echo "[DEBUG] Listing strategies/:" \
    && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

# 複製專案檔案
COPY . .

# 再次檢查 trend.py 在專案完整複製後是否存在
RUN echo "[DEBUG] After COPY . :" \
    && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

# 啟動應用
CMD ["python", "main.py"]
