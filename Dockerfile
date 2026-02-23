FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY src/ src/
COPY notebook/data/ notebook/data/
COPY notebook/artifacts/ notebook/artifacts/
COPY artifacts/ artifacts/
COPY model/ model/

# Expose port
EXPOSE 8000

# Run the app — artifacts auto-retrain if missing or incompatible
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
