FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "import razorpay; print('Razorpay SDK installed:', razorpay.__version__ if hasattr(razorpay, '__version__') else 'installed')"

# Copy backend application source
COPY backend ./backend

# Create required runtime upload directories
RUN mkdir -p /app/backend/uploads/qr /app/backend/uploads/screenshots

WORKDIR /app/backend

# Use shell form of CMD so $PORT is evaluated at container runtime
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
