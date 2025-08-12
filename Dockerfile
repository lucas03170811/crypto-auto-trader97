FROM python:3.11-slim

WORKDIR /app

# 安裝必要套件（build 工具）
RUN apt-get update && apt-get install -y \
    build-essential wget git && apt-get clean

# 複製 requirements 與安裝
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼
COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
