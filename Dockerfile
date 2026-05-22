# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install necessary system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code
COPY . .

# Ensure cache directories exist
RUN mkdir -p audio_cache image_cache chats

# Expose the internal Gradio/FastAPI port
EXPOSE 7861

# Start the application using Gunicorn with Uvicorn async workers for high concurrency
CMD ["gunicorn", "lumina.ui.interface:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:7861", "--timeout", "120"]
