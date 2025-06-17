FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Set work directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 10000

# Start app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
