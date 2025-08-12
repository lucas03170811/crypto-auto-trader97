# 使用 Python 基礎映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案所有檔案
COPY . .

# ✅ 在 COPY 之後檢查 /app 目錄結構，並驗證 trend.py 是否存在
RUN echo "[DEBUG] Listing /app after COPY:" \
    && ls -R /app \
    && if [ -f /app/strategies/trend.py ]; then \
           echo "[DEBUG] trend.py FOUND ✅"; \
       else \
           echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; \
       fi

# 設定容器啟動指令
CMD ["python", "main.py"]
