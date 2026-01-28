---
title: Agentic Honey Pot
emoji: 🍯
colorFrom: yellow
colorTo: orange
sdk: docker
app_port: 7860
pinned: false
---

# Agentic Honey-Pot System 🍯🤖

**Autonomous scam detection and intelligence extraction using local LLM**

A hackathon-ready API that detects scam messages, engages scammers in natural conversations, and extracts intelligence (bank accounts, UPI IDs, phishing links) - all using **100% free, local resources**.

## 🎯 Features

- **Scam Detection**: Binary classification on initial message using local LLM
- **Autonomous Agent**: Maintains believable persona (Ramesh Patel, elderly Mumbai resident)
- **Intelligence Extraction**: Regex + LLM parsing for banks, UPIs, phishing links
- **Multi-turn Conversations**: Handles 5-15 turn conversations with memory
- **Structured Output**: JSON responses with extracted intelligence and metrics
- **API Key Authentication**: Secure webhook endpoint
- **Zero Paid Services**: No cloud LLM APIs, no external dependencies

## 🏗️ Architecture

```
┌─────────────────┐
│ Mock Scammer    │
│ API (Evaluator) │
└────────┬────────┘
         │ POST /webhook
         │ {session_id, message}
         ▼
┌─────────────────────────────────┐
│  FastAPI Server                 │
│  ┌───────────────────────────┐  │
│  │ 1. Auth (API Key)         │  │
│  │ 2. Scam Detection (LLM)   │  │
│  │ 3. Agent Reply (LLM)      │  │
│  │ 4. Extraction (Regex)     │  │
│  │ 5. Session Management     │  │
│  └───────────────────────────┘  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Ollama (Local)  │
│ Qwen2.5-7B      │
└─────────────────┘
```

## 📋 Requirements

- Python 3.10+
- Ollama (for local LLM)
- 8GB+ RAM (16GB recommended)
- CPU or GPU (GPU recommended for faster inference)

## 🚀 Quick Start

### 1. Install Ollama

**Windows:**
```powershell
# Download from https://ollama.com/download/windows
# Or use winget
winget install Ollama.Ollama
```

**Linux/Mac:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull the Model

```bash
ollama pull qwen2.5:7b-instruct-q5_K_M
```

**Alternative models** (if Qwen doesn't work):
```bash
# Smaller, faster (weaker Indic support)
ollama pull llama3.2:3b-instruct-q4_K_M

# Larger, better quality
ollama pull gemma2:9b-instruct-q5_K_M
```

### 3. Install Dependencies

```bash
cd fusion-meteoroid
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set your API key
# API_KEY=your-secret-key-2026
```

### 5. Start Ollama Server

```bash
ollama serve
```

Keep this running in a separate terminal.

### 6. Run the API

```bash
python app.py
```

Server will start at `http://localhost:8000`

### 7. Test the API

In a new terminal:

```bash
python test_api.py
```

## 📡 API Endpoints

### POST `/webhook`

Main endpoint for scam conversation handling.

**Request:**
```json
{
  "session_id": "abc123",
  "message": "Hello sir, your ATM card is blocked..."
}
```

**Headers:**
```
X-API-Key: your-secret-key-2026
```

**Response:**
```json
{
  "reply": "Namaste, kya problem hai beta?",
  "extracted": {
    "banks": ["SBIN0001234", "9876543210123456"],
    "upis": ["scammer@paytm"],
    "phishing_links": ["https://fake-icici.com"]
  },
  "done": false
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "model": "qwen2.5:7b-instruct-q5_K_M",
  "sessions_active": 3
}
```

### GET `/metrics/{session_id}`

Get detailed metrics for a session.

**Headers:**
```
X-API-Key: your-secret-key-2026
```

**Response:**
```json
{
  "session_id": "abc123",
  "detected_scam": true,
  "turn_count": 8,
  "duration_seconds": 45.2,
  "extracted_info": {
    "banks": ["SBIN0001234"],
    "upis": ["scammer@paytm"],
    "phishing_links": ["https://fake-bank.com"]
  },
  "conversation_log": [
    {
      "role": "scammer",
      "content": "Hello sir...",
      "timestamp": "2026-01-27T01:30:00"
    },
    ...
  ]
}
```

### DELETE `/sessions/{session_id}`

Delete a session (cleanup).

## 🧪 Testing

### Manual Testing with cURL

```bash
# Test scam detection
curl -X POST http://localhost:8000/webhook \
  -H "X-API-Key: your-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test1",
    "message": "Your ATM card is blocked. Share OTP to unblock."
  }'

# Check health
curl http://localhost:8000/health

# Get metrics
curl http://localhost:8000/metrics/test1 \
  -H "X-API-Key: your-secret-key-2026"
```

### Automated Test Suite

```bash
python test_api.py
```

Tests include:
- ✅ Health check
- ✅ Authentication (valid/invalid API keys)
- ✅ Scam detection accuracy
- ✅ Non-scam rejection (false positive check)
- ✅ Multi-turn conversation flow
- ✅ Intelligence extraction
- ✅ Metrics endpoint

## 🚢 Deployment (Hugging Face Spaces - Free Tier)

Hugging Face Spaces is the recommended deployment platform for this project, as it provides **16GB RAM and 2 vCPUs** on its free Docker tier, making it ideal for running local LLMs like Llama 3.2.

### 1. Create a Space
1. Log in to [huggingface.co](https://huggingface.co) and click **"New Space"**.
2. Select **Docker** as the SDK and choose the **Blank** template.
3. In **Settings -> Variables and secrets**, add a secret named `API_KEY` with your chosen production key.

### 2. Prepare and Push Code
Add Hugging Face as a remote and push your main branch:
```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git add .
git commit -m "Deploying to Hugging Face Spaces"
git push hf main --force
```

**Note**: The app is configured to run on port **7860** (mandatory for HF Spaces). The startup script will automatically pull the optimized **Llama 3.2 1B** model.

## 📊 Evaluation Metrics

The system tracks metrics aligned with hackathon evaluation:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Detection Accuracy | >90% | Test with 20 scam/non-scam samples |
| Engagement Duration | 8-12 turns avg | Check `turn_count` in metrics |
| Extraction Completeness | >70% | Count extracted items vs available |
| False Positives | <5% | Test with legitimate messages |
| Response Latency | <5s | Monitor logs |

## 🎭 Persona Details

**Ramesh Patel** - The AI Agent
- Age: 62, retired bank employee
- Location: Mumbai
- Language: Hinglish (Hindi-English mix)
- Traits: Trusting, slightly confused about tech, helpful
- Goal: Extract scammer's payment details naturally

**Example Conversation:**
```
Scammer: "Sir, your account is compromised. Share OTP."
Ramesh: "Arre, kya hua beta? I don't understand OTP. Can you help?"
Scammer: "Sir, check SMS and tell me the 6-digit code."
Ramesh: "Ok ok, but first tell me where to send money if needed? Your account number?"
```

## 🔧 Troubleshooting

### Ollama Connection Error

```bash
# Check if Ollama is running
ollama list

# Restart Ollama
# Windows: Restart Ollama from system tray
# Linux/Mac: killall ollama && ollama serve
```

### Model Not Found

```bash
# Re-pull the model
ollama pull qwen2.5:7b-instruct-q5_K_M

# Or use alternative
ollama pull llama3.2:3b-instruct-q4_K_M
```

### Slow Inference

- Use smaller model: `llama3.2:3b`
- Reduce `max_tokens` in `app.py`
- Use quantized models (q4_K_M instead of q5_K_M)

### Memory Issues

- Close other applications
- Use lighter model (3B instead of 7B)
- Reduce `MAX_HISTORY_TURNS` in `.env`

## 📝 Configuration

Edit `.env` to customize:

```bash
# API Security
API_KEY=your-secret-key-2026

# Model Selection
OLLAMA_MODEL=qwen2.5:7b-instruct-q5_K_M

# Conversation Limits
MAX_TURNS=15              # Max conversation length
MAX_HISTORY_TURNS=12      # Context window size

# Server
PORT=8000
DEBUG=false               # Set true to show detailed errors
```

## 🎯 Success Criteria (Hackathon)

- [x] Public HTTPS endpoint (via Render)
- [x] API key authentication
- [x] Scam detection (binary classification)
- [x] Multi-turn autonomous engagement
- [x] Intelligence extraction (banks, UPIs, links)
- [x] Structured JSON output
- [x] 100% local LLM (no paid APIs)
- [x] Session metrics for evaluation
- [x] <5s response latency
- [x] Handles 10+ concurrent sessions

## 🚫 Inversions (What We Avoid)

- ❌ No paid LLM APIs (GPT, Claude, Groq)
- ❌ No cloud inference services
- ❌ No databases (in-memory only)
- ❌ No infinite loops (capped at 15 turns)
- ❌ No revealing detection to scammer
- ❌ No real personal data exposure

## 📚 Tech Stack

- **Framework**: FastAPI 0.109
- **LLM**: Ollama (Llama 3.2 1B)
- **Extraction**: Regex + LLM parsing
- **Storage**: In-memory (defaultdict)
- **Deployment**: Hugging Face Spaces (Docker)
- **Testing**: Python requests

## 🤝 Contributing

This is a hackathon project. For improvements:

1. Fork the repo
2. Create feature branch
3. Test with `test_api.py`
4. Submit PR

## 📄 License

MIT License - Free for hackathon and educational use.

## 🙏 Acknowledgments

- Ollama team for local LLM infrastructure
- Qwen team for multilingual model
- FastAPI for excellent API framework

---

**Built for hackathons. No paid services. 100% local. 🚀**
