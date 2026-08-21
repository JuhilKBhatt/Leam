# Use Python 3.14 (latest stable)
FROM python:3.14-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (including VAAPI drivers for AMD GPU acceleration)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    mesa-va-drivers \
    intel-media-va-driver \
    libva-drm2 \
    libva2 \
    vainfo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p data

# Make start.sh executable
RUN chmod +x start.sh

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["./start.sh"]
