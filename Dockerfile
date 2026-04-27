# Dockerfile for OpenClaw Dashboard
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend
COPY frontend/ ./frontend/

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Set environment
ENV PYTHONUNBUFFERED=1
ENV DASHBOARD_DB_PATH=/app/data/dashboard.db

# Run the dashboard
CMD ["python", "backend/main.py"]
