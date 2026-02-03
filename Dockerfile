FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Create data directory
RUN mkdir -p data

# Default config (can be overridden by volume mount)
COPY config.yaml .

EXPOSE 8080

# Run with gunicorn for production
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "app:app"]
