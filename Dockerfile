FROM python:3.11-slim

# 安裝系統編譯工具和 TA-Lib 依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    tar \
    && apt-get clean

# 安裝 TA-Lib 原生庫
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib && ./configure --prefix=/usr && make && make install \
    && cd .. && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# 更新 pip 並安裝 Python 套件
RUN pip install --upgrade pip

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt 並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 強制重新複製專案（避免 cache）
ARG CACHEBUST
RUN echo "CACHEBUST=${CACHEBUST}"
COPY . .

# 檢查 strategies/trend.py 是否存在
RUN echo "===== /app tree =====" && ls -R /app || true \
    && echo "===== /app/strategies =====" && ls -l /app/strategies || true \
    && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

# 啟動
CMD ["python", "main.py"]
