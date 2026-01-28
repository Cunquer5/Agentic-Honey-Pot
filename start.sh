#!/bin/bash

# Start script for Render.com
# Starts Ollama server in background, then FastAPI

echo "🚀 Starting Agentic Honey-Pot server..."

# Start Ollama in background (if available)
if command -v ollama &> /dev/null; then
    echo "🔧 Starting Ollama server..."
    ollama serve &
    
    # Wait for Ollama to be ready
    sleep 5
    
    # Ensure model is available
    echo "📥 Checking model ${OLLAMA_MODEL:-llama3.2:1b-instruct-q4_K_M}..."
    ollama pull ${OLLAMA_MODEL:-llama3.2:1b-instruct-q4_K_M}
    
    echo "✅ Ollama ready"
else
    echo "⚠️  Ollama not available - LLM calls will fail"
fi

# Start FastAPI application
echo "🌐 Starting FastAPI server on port ${PORT:-7860}..."
python app.py
