FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && apt-get clean

# 複製與安裝 requirements
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 複製程式碼
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
