FROM python:3.12-slim

# Cài đặt các thư viện hệ thống
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy mã nguồn
COPY . .

# Chạy ứng dụng
CMD ["python", "bot.py"]