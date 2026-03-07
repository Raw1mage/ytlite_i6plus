# Use official Python lightweight image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg and git are essential for yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the Flask port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
