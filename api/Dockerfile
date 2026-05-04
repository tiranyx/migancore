FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Day 41: weasyprint needs cairo + pango + gdk-pixbuf; marp-cli needs nodejs (chromium for PPTX renderer)
# Day 42 prep: nodejs also needed for HYPERX subprocess integration
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu \
    nodejs \
    npm \
    chromium \
    && npm install -g @marp-team/marp-cli@4 \
    && rm -rf /var/lib/apt/lists/*

# Tell marp/puppeteer where chromium is (avoids second download)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
