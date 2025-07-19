FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    libproj-dev \
    proj-data \
    proj-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary project files
COPY main.py .
COPY src/ ./src/


# Expose Dash default port
EXPOSE 8050

# Set environment variable to suppress interactive prompts during package installations
ENV NON_INTERACTIVE=1

# Run the Dash app
CMD ["python", "main.py"]