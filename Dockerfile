# 使用 Python 3.11 slim 版本
FROM python:3.11-slim

# 強制重新複製檔案（自動時間戳避免快取）
ARG CACHEBUST=1
ENV CACHEBUST=${CACHEBUST}

# 設定工作目錄
WORKDIR /app

# 安裝基礎系統套件（不裝 libta-lib，改用 ta-lib-bin）
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    tar \
    libffi-dev \
    libssl-dev \
    python3-dev \
    gcc \
    make \
    && rm -rf /var/lib/apt/lists/*

# 先複製 requirements.txt 並安裝
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 複製專案檔案
COPY . .

# 預設啟動指令
CMD ["python", "main.py"]
