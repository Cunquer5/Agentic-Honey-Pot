# 🚀 Quick Start Guide - Agentic Honey-Pot

## Prerequisites Check

Before starting, ensure you have:
- [ ] Python 3.10 or higher installed
- [ ] 8GB+ RAM available
- [ ] Internet connection (for initial model download)

## Step-by-Step Setup (5 minutes)

### 1. Install Ollama

**Windows:**
```powershell
# Download installer from https://ollama.com/download/windows
# Or use winget:
winget install Ollama.Ollama
```

**Verify installation:**
```powershell
ollama --version
```

### 2. Pull the LLM Model

```powershell
ollama pull qwen2.5:7b-instruct-q5_K_M
```

This will download ~4.7GB. Wait for completion.

**Alternative (if above fails):**
```powershell
# Smaller, faster model
ollama pull llama3.2:3b-instruct-q4_K_M
```

Then update `.env` file:
```
OLLAMA_MODEL=llama3.2:3b-instruct-q4_K_M
```pi

### 3. Install Python Dependencies

```powershell
cd c:\Users\AAKASH\.gemini\antigravity\playground\fusion-meteoroid
pip install -r requirements.txt
```

### 4. Start Ollama Server

Open a **new terminal** and run:
```powershell
ollama serve
```

Keep this terminal open. You should see:
```
Ollama is running
```

### 5. Start the API Server

In your **original terminal**:
```powershell
python app.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6. Test the System

Open a **third terminal** and run:
```powershell
# Quick health check
curl http://localhost:8000/health

# Run full test suite
python test_api.py

# Or run interactive simulation
python mock_scammer.py
```

## Expected Output

### Health Check
```json
{
  "status": "ok",
  "model": "qwen2.5:7b-instruct-q5_K_M",
  "sessions_active": 0
}
```

### Test Conversation
```
=== Testing Scam Conversation ===
Session ID: test_1738012345

--- Turn 1 ---
Scammer: Hello sir, your ATM card is blocked...
Agent: Namaste, kya problem hai beta? I don't understand...
Extracted: {"banks": [], "upis": [], "phishing_links": []}
Done: False

--- Turn 2 ---
Scammer: Sir, send money to verify@paytm
Agent: Arre, what is your account number? I will send...
Extracted: {"banks": [], "upis": ["verify@paytm"], "phishing_links": []}
Done: False
...
```

## Troubleshooting

### "Connection refused" error
- **Cause**: Ollama server not running
- **Fix**: Run `ollama serve` in separate terminal

### "Model not found" error
- **Cause**: Model not downloaded
- **Fix**: Run `ollama pull qwen2.5:7b-instruct-q5_K_M`

### Slow responses (>10s)
- **Cause**: CPU-only inference or large model
- **Fix**: Use smaller model `llama3.2:3b-instruct-q4_K_M`

### "Invalid API key" error
- **Cause**: API key mismatch
- **Fix**: Check `.env` file and test script use same key

## Next Steps

1. **Run benchmarks**: `python benchmark.py`
2. **Test with Postman**: Import API docs from `http://localhost:8000/docs`
3. **Deploy to Render**: Follow README.md deployment section
4. **Customize persona**: Edit `generate_agent_reply()` in `app.py`

## Quick Commands Reference

```powershell
# Start Ollama (Terminal 1)
ollama serve

# Start API (Terminal 2)
python app.py

# Run tests (Terminal 3)
python test_api.py          # Automated tests
python mock_scammer.py      # Interactive simulation
python benchmark.py         # Performance benchmarks

# Manual API test
curl -X POST http://localhost:8000/webhook ^
  -H "X-API-Key: your-secret-key-2026" ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\": \"test1\", \"message\": \"Your account is blocked\"}"
```

## Success Checklist

- [ ] Ollama installed and running
- [ ] Model downloaded (check with `ollama list`)
- [ ] Python dependencies installed
- [ ] API server starts without errors
- [ ] Health check returns 200 OK
- [ ] Test suite passes (>80% tests green)
- [ ] Mock conversation completes successfully

## Support

If you encounter issues:

1. Check logs in terminal where `python app.py` is running
2. Verify Ollama is running: `ollama list`
3. Test model directly: `ollama run qwen2.5:7b-instruct-q5_K_M "Hello"`
4. Check Python version: `python --version` (should be 3.10+)

---

**Ready for hackathon! 🎉**
