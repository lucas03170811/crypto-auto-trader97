FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴（若需要編譯套件）
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    wget \
    git \
    && apt-get clean

# 複製 requirements 並安裝
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 確認 strategies/trend.py 存在（幫 debug）
RUN echo "[DEBUG] Listing /app:" && ls -R /app || true \
 && if [ -f /app/strategies/trend.py ]; then echo "[DEBUG] trend.py FOUND ✅"; else echo "[ERROR] trend.py NOT FOUND ❌" && exit 1; fi

ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]
