FROM python:3.10-slim

# Install system dependencies including Tesseract OCR and Thai language data
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tha \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy all code
COPY . /app/

# Set environment variables for Tesseract
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Expose port (Cloud Run defaults to 8080, but can be overridden)
ENV PORT=8080
EXPOSE $PORT

# Start command (Cloud Run passes the PORT environment variable)
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
