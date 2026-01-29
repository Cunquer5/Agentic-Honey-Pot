FROM python:3.11-slim

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set up a non-root user for Hugging Face (UID 1000)
# We use '|| true' in case the user already exists in the base image
RUN useradd -m -u 1000 user || true

# Create app directory and set permissions
WORKDIR /app
RUN chown -R user:user /app

# Switch to the non-root user
USER user
ENV HOME=/home/user
ENV PATH="/home/user/.local/bin:${PATH}"
ENV OLLAMA_HOST=127.0.0.1
ENV OLLAMA_HOME=/home/user/.ollama

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
