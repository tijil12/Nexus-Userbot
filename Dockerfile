FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    make \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY main.py .
COPY start.sh .

# Make start script executable
RUN chmod +x start.sh

# Run the bot
CMD ["./start.sh"]
