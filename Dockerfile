FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment setup
ENV PYTHONUNBUFFERED=1

# Command to run the application (assuming we want it to run once and exit, ideal for cron jobs, or we can use cron within the container. Here we run main.py directly)
CMD ["python", "main.py"]
