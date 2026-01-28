#!/bin/bash

# Deployment script for Render.com
# This script is called during Render build process

echo "🚀 Starting Agentic Honey-Pot deployment..."

# Install Python dependencies
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Check if Ollama is available (might not be on Render free tier)
if command -v ollama &> /dev/null; then
    echo "✅ Ollama found"
    
    # Pull the model
    echo "📥 Pulling LLM model (this may take a few minutes)..."
    ollama pull ${OLLAMA_MODEL:-llama3.2:1b-instruct-q4_K_M}
    
    echo "✅ Model ready"
else
    echo "⚠️  Ollama not found - will need to be installed separately"
    echo "   For Render deployment, you may need to use Docker"
fi

echo "✅ Deployment preparation complete"
