# 使用 Python 3.11 輕量版
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝必要套件
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    && apt-get clean

# 升級 pip
RUN pip install --upgrade pip

# 安裝 numpy 版本鎖定（避免 talib 相依性錯誤）
RUN pip install numpy==1.24.4

# 先複製 requirements.txt 並安裝套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 加入 CACHEBUST 機制讓 COPY 強制刷新
ARG CACHEBUST=$(date +%s)

# 複製所有程式碼到容器
COPY . .

# ✅ 檢查檔案結構，確保 strategies/trend.py 存在
RUN echo "===== /app tree =====" && ls -R /app || true \
    && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo '[DEBUG] trend.py FOUND ✅'; else echo '[ERROR] trend.py NOT FOUND ❌' && exit 1; fi

# 啟動容器後執行 main.py
CMD ["python", "main.py"]
