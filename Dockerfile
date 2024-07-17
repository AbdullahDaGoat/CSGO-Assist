# Use the official Python image from Docker Hub
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        libglib2.0-0 \
        libnss3 \
        libgconf-2-4 \
        libfontconfig1 \
        wget \
        ca-certificates \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN python -m pip install playwright
RUN playwright install

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire current directory into the container
COPY . .

# Expose the port that Flask runs on
EXPOSE 443

# Run the Flask application
CMD ["python", "your_script_name.py"]
