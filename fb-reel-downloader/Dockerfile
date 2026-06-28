FROM python:3.12-slim

# ffmpeg 讓 yt-dlp 在遇到音畫分離的影片時可以合併（reel 多半已合好，但裝著保險）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

ENV PORT=8000
EXPOSE 8000

# gunicorn 單 worker、長 timeout（大檔下載可能要幾十秒）
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --timeout 300 server:app"]
