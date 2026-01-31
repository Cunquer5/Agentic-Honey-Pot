FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    sed \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama binary
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/bin/ollama && \
    chmod +x /usr/bin/ollama

# Set up non-root user for Hugging Face (UID 1000)
RUN useradd -m -u 1000 user || echo "User exists"

WORKDIR /app

# Install Python dependencies globally as root first for stability
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Fix line endings and permissions for start.sh
RUN sed -i 's/\r$//' start.sh && \
    chmod +x start.sh && \
    chown -R user:user /app

# Switch to non-root user
USER user
ENV HOME=/home/user
ENV PATH="/home/user/.local/bin:${PATH}"
ENV OLLAMA_HOST=localhost
ENV OLLAMA_HOME=/home/user/.ollama

# Ensure Ollama directory exists
RUN mkdir -p /home/user/.ollama

EXPOSE 7860
CMD ["bash", "start.sh"]
