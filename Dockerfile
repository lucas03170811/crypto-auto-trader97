FROM python:3.11-slim

WORKDIR /app

# 安裝必要 build 工具（部分套件需要）
RUN apt-get update && apt-get install -y build-essential wget git && apt-get clean

# 複製 requirements 並安裝（先安裝 numpy 以避免編譯/相容問題）
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
