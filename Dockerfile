FROM python:3.11-slim

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables for HTTP transport
ENV TRANSPORT=http
ENV PORT=8081
ENV HOST=0.0.0.0

# Expose the port
EXPOSE 8081

# Health check not needed - Smithery will detect running server

# Run the server
CMD ["python3", "server.py"]