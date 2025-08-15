FROM python:3.11-slim

# 讓 Python 不產生 .pyc、stdout 立即刷新（可選）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 用時間戳避免 COPY 快取
ARG CACHEBUST
RUN echo "CACHEBUST=$(date +%s)"

WORKDIR /app

# 先裝相依
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 再複製專案
COPY . .

CMD ["python", "main.py"]
