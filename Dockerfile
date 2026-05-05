FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "studio_app.py", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--server.address=0.0.0.0", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
