# 使用 Python 3.11 slim 版
FROM python:3.11-slim

# 加速 cache bust
RUN echo "CACHEBUST=$(date +%s)"

WORKDIR /app

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 pip + 套件
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 複製專案檔案
COPY . .

# 預設啟動指令
CMD ["python", "main.py"]
