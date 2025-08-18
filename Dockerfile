FROM python:3.11-slim

WORKDIR /app

# 先裝套件
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 再複製專案
COPY . .

# Railway 預設入口（也可在 Railway 直接設定）
CMD ["python", "main.py"]
