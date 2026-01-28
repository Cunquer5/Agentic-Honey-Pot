FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create a non-root user (Hugging Face uses UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"
ENV OLLAMA_HOST=127.0.0.1
ENV OLLAMA_HOME=/home/user/.ollama

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=user:user . .

# Expose Hugging Face default port
EXPOSE 7860

# Ensure start.sh is executable
RUN chmod +x start.sh

# Start script
CMD ["bash", "start.sh"]
