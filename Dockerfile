FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama binary directly (more reliable in Docker than the script)
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/bin/ollama && \
    chmod +x /usr/bin/ollama

# Hugging Face already has a user with UID 1000 in their runtime environment.
# We will create a local user to match that UID for build-time compatibility.
RUN useradd -m -u 1000 user || echo "User already exists"

# Set up environment and directories
WORKDIR /app
RUN chown -R user:user /app
USER user
ENV HOME=/home/user
ENV PATH="/home/user/.local/bin:${PATH}"
ENV OLLAMA_HOST=127.0.0.1
ENV OLLAMA_HOME=/home/user/.ollama

# Create Ollama directory with proper permissions
RUN mkdir -p /home/user/.ollama && chown -R user:user /home/user/.ollama

# Install Python dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application files
COPY --chown=user:user . .

# Ensure scripts are executable
RUN chmod +x start.sh

# Deployment config
EXPOSE 7860
CMD ["bash", "start.sh"]
