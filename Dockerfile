# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Python finds local modules
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Run your scanner
CMD ["python", "main.py"]
