# Use Python 3.12 (stable, has pre-built wheels for faster install)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (including VAAPI drivers for AMD GPU acceleration and Remotion requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    mesa-va-drivers \
    libva-drm2 \
    libva2 \
    vainfo \
    nodejs \
    npm \
    chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js dependencies for Remotion (creates linux binaries)
# Done before copying the rest of the app to leverage Docker cache
COPY remotion/package*.json ./remotion/
RUN cd remotion && npm install

# Copy the rest of the application code
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p data

# Make start.sh executable
RUN chmod +x start.sh

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["bash", "start.sh"]
