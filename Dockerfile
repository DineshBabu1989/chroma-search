# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with specific order
RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.11.4
RUN pip install --no-cache-dir torch==2.2.0
RUN pip install --no-cache-dir transformers==4.36.2 huggingface-hub==0.20.3
RUN pip install --no-cache-dir sentence-transformers==2.2.2
RUN pip install --no-cache-dir pandas==2.1.4 scikit-learn==1.3.2
RUN pip install --no-cache-dir chromadb==0.4.22
RUN pip install --no-cache-dir fastapi==0.104.1 uvicorn[standard]==0.24.0 python-multipart==0.0.6
RUN pip install --no-cache-dir openpyxl==3.1.2 requests==2.31.0 tqdm==4.66.1

# Copy application files
COPY main.py .
COPY static/ ./static/

# Create directories for data (models will be mounted from host)
RUN mkdir -p chroma_db uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["python", "main.py"] 