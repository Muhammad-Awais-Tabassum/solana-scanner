FROM python:3.10

# Install OS dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    wget \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libx11-xcb1 \
    libx11-dev \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps
CMD ["python", "main.py"]