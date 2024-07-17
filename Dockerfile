# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and its dependencies
RUN pip install playwright -U undetected-playwright && playwright install-deps

# Install Flask and other Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 443

# Specify the command to run your application
CMD ["python", "app.py"]
