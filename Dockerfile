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

# 先複製 requirements.txt，改動會觸發重新安裝套件
COPY requirements.txt .

# 顯示 requirements.txt 並安裝
RUN echo "======= REQUIREMENTS CONTENT =======" && cat requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

# 驗證 pandas_ta 是否成功安裝
RUN python -c "import pandas_ta; print('[CHECK] pandas_ta installed, version:', pandas_ta.__version__)"

# 複製程式碼
COPY . .

# 顯示 binance_client.py 內容做 Debug
RUN echo "======= CHECK binance_client.py CONTENT =======" && cat exchange/binance_client.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
