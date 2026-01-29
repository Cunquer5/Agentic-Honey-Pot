FROM python:3.11-slim

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama binary directly (more reliable in Docker)
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/bin/ollama && \
    chmod +x /usr/bin/ollama

# Hugging Face already has a user with UID 1000 in their runtime environment.
# We create it locally for build compatibility.
RUN useradd -m -u 1000 user || echo "User exists"

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

# Copy requirements first for better caching
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application
COPY --chown=user:user . .

# Ensure start.sh is executable
RUN chmod +x start.sh

# Expose Hugging Face default port
EXPOSE 7860

# Start script
CMD ["bash", "start.sh"]
