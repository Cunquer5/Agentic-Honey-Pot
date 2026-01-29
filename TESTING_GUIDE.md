# 🧪 Testing Guide - Agentic Honey-Pot System

## Overview

This guide explains how to test your Agentic Honey-Pot system to verify it's working correctly. There are **4 testing methods** ranging from quick checks to comprehensive evaluations.

---

## Prerequisites

Before testing, ensure:
- ✅ Ollama is installed and running (`ollama serve`)
- ✅ Model is downloaded (`ollama pull qwen2.5:7b-instruct-q5_K_M`)
- ✅ API server is running (`python app.py`)
- ✅ `.env` file is configured with correct API key

---

## Testing Methods

### 🟢 Method 1: Quick Health Check (5 seconds)

**Purpose**: Verify API server and Ollama connection

**Command**:
```powershell
curl http://localhost:8000/health
```

**Expected Output**:
```json
{
  "status": "ok",
  "model": "qwen2.5:7b-instruct-q5_K_M",
  "sessions_active": 0
}
```

**What it tests**:
- ✓ API server is running
- ✓ Ollama connection is working
- ✓ Model is loaded
- ✓ Session tracking is functional

---

### 🟡 Method 2: Automated Test Suite (2-3 minutes)

**Purpose**: Comprehensive testing of all API features

**Command**:
```powershell
python test_api.py
```

**What it tests**:
- ✓ Health endpoint
- ✓ API key authentication (valid/invalid)
- ✓ Scam detection accuracy
- ✓ Non-scam message rejection (false positive check)
- ✓ Multi-turn conversation flow
- ✓ Intelligence extraction (banks, UPIs, phishing links)
- ✓ Metrics endpoint
- ✓ Session management

**Expected Output**:
```
============================================================
AGENTIC HONEY-POT API TEST SUITE
============================================================

=== Testing Health Endpoint ===
Status: 200
Response: {
  "status": "ok",
  "model": "qwen2.5:7b-instruct-q5_K_M",
  "sessions_active": 0
}

=== Testing Authentication ===
Without API key: 401 (expected 401)
With wrong API key: 401 (expected 401)
With correct API key: 200 (expected 200)

=== Testing Non-Scam Detection ===
Message: Hi, I'm calling about the apartment...
Done immediately: True
Reply: ''
✓ Correctly identified as non-scam

=== Testing Scam Conversation ===
Session ID: test_1738012345

--- Turn 1 ---
Scammer: Hello sir, this is from State Bank of India...
Agent: Namaste, kya problem hai beta? I don't understand...
Extracted: {"banks": [], "upis": [], "phishing_links": []}
Done: False

--- Turn 2 ---
Scammer: Yes sir, I need your account number...
Agent: Arre, what is your account number? I will send...
Extracted: {"banks": [], "upis": [], "phishing_links": []}
Done: False

[... more turns ...]

=== Testing Metrics Endpoint ===
Metrics:
  Detected as scam: True
  Total turns: 4
  Duration: 12.34s
  Extracted info:
    Banks: ['SBIN0001234']
    UPIs: ['scammer@paytm']
    Links: ['https://fake-bank.com/verify']

============================================================
TEST SUITE COMPLETED
============================================================
```

---

### 🔵 Method 3: Interactive Mock Scammer (5-10 minutes)

**Purpose**: Realistic end-to-end simulation with a mock scammer bot

**Command**:
```powershell
python mock_scammer.py
```

**What it tests**:
- ✓ Full conversation flow (5-15 turns)
- ✓ Agent persona believability
- ✓ Natural language understanding
- ✓ Intelligence extraction in context
- ✓ Conversation termination logic
- ✓ Real-time response quality

**Expected Output**:
```
========================================
Mock Scammer Simulation
========================================

Starting conversation with session: mock_1738012345

[Turn 1]
Scammer → Agent: Hello sir, this is from HDFC Bank security...
Agent → Scammer: Namaste beta, kya hua? I am not understanding...

[Turn 2]
Scammer → Agent: Sir, someone tried to withdraw Rs 50,000...
Agent → Scammer: Arre! That is my money! How to stop this?...

[... conversation continues ...]

[Turn 8]
Scammer → Agent: Send Rs 100 to verify@paytm to verify...
Agent → Scammer: Ok ok, but what is your account number also?

========================================
Conversation Summary
========================================
Total Turns: 8
Duration: 45.2 seconds
Intelligence Extracted:
  - Banks: SBIN0001234, 9876543210123456
  - UPIs: verify@paytm
  - Phishing Links: https://fake-hdfc.com/verify
```

---

### 🟣 Method 4: Performance Benchmark (10-15 minutes)

**Purpose**: Measure system performance and scalability

**Command**:
```powershell
python benchmark.py
```

**What it tests**:
- ✓ Response latency (avg, p50, p95, p99)
- ✓ Throughput (requests per second)
- ✓ Concurrent session handling
- ✓ Memory usage
- ✓ Detection accuracy across 50+ test cases
- ✓ Extraction completeness rate

**Expected Output**:
```
========================================
Performance Benchmark
========================================

Running 50 test conversations...
Progress: [####################] 100%

Results:
  Detection Accuracy: 94.0% (47/50)
  False Positive Rate: 4.0% (2/50)
  
  Response Latency:
    Average: 2.3s
    P50: 2.1s
    P95: 4.5s
    P99: 6.2s
  
  Extraction Completeness:
    Banks: 78% (39/50)
    UPIs: 82% (41/50)
    Links: 71% (35/50)
  
  Throughput: 12.5 req/min
  Memory Usage: 1.2 GB
  
✓ All metrics within acceptable range
```

---

## 🚀 Quick Test Runner (Windows)

For convenience, use the interactive test runner:

```powershell
.\run_tests.bat
```

**Menu Options**:
1. Quick Test (health check only)
2. Full Test Suite
3. Mock Scammer Simulation
4. Performance Benchmark
5. All Tests

---

## Manual API Testing

### Using cURL

**Test scam detection**:
```powershell
curl -X POST http://localhost:8000/webhook `
  -H "X-API-Key: your-secret-key-2026" `
  -H "Content-Type: application/json" `
  -d "{\"sessionId\": \"manual_test_1\", \"message\": {\"sender\": \"scammer\", \"text\": \"Your ATM card is blocked. Share OTP to unblock.\"}}"
```

**Check metrics**:
```powershell
curl http://localhost:8000/metrics/manual_test_1 `
  -H "X-API-Key: your-secret-key-2026"
```

### Using Postman

1. Import the API collection: `postman_collection.json`
2. Set environment variable: `API_KEY = your-secret-key-2026`
3. Run the collection tests

### Using Swagger UI

1. Open browser: `http://localhost:8000/docs`
2. Click "Authorize" and enter API key
3. Test endpoints interactively

---

## Troubleshooting Test Failures

### ❌ "Connection refused" error

**Cause**: API server not running

**Fix**:
```powershell
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start API
python app.py
```

---

### ❌ "Model not found" error

**Cause**: Model not downloaded

**Fix**:
```powershell
ollama pull qwen2.5:7b-instruct-q5_K_M
```

---

### ❌ "Invalid API key" error

**Cause**: API key mismatch between `.env` and test scripts

**Fix**:
1. Check `.env` file: `API_KEY=your-secret-key-2026`
2. Check `test_api.py` line 13: `API_KEY = "your-secret-key-2026"`
3. Ensure they match exactly

---

### ❌ Slow responses (>10s)

**Cause**: CPU-only inference or large model

**Fix**:
```powershell
# Use smaller, faster model
ollama pull llama3.2:3b-instruct-q4_K_M
```

Update `.env`:
```
OLLAMA_MODEL=llama3.2:3b-instruct-q4_K_M
```

---

### ❌ Low detection accuracy (<80%)

**Cause**: Model not suitable or prompt issues

**Fix**:
1. Try different model: `gemma2:9b-instruct-q5_K_M`
2. Check Ollama logs for errors
3. Verify model is fully downloaded: `ollama list`

---

## Success Criteria

Your system is working correctly if:

- ✅ Health check returns 200 OK
- ✅ Authentication tests pass (401 for invalid, 200 for valid)
- ✅ Scam detection accuracy >85%
- ✅ Non-scam rejection rate >90% (low false positives)
- ✅ Multi-turn conversations complete (5-15 turns)
- ✅ Intelligence extraction finds at least 1 item per conversation
- ✅ Response latency <5s average
- ✅ Metrics endpoint returns complete data

---

## Test Data Reference

### Scam Message Examples (from `test_api.py`)

1. **Bank impersonation**: "Hello sir, this is from State Bank of India. Your ATM card is blocked..."
2. **UPI scam**: "Congratulations! You have won Rs 50,000 in Google Pay lucky draw..."
3. **Phishing link**: "Dear customer, your account will be suspended. Click https://fake-icici-login.com..."
4. **OTP scam**: "This is HDFC Bank security. We detected unauthorized transaction..."
5. **Investment scam**: "Sir, I am calling from Stock Market Advisory. Invest Rs 10,000..."

### Non-Scam Message Examples

1. "Hi, I'm calling about the apartment you listed for rent..."
2. "Hello, this is a reminder about your doctor's appointment..."
3. "Hey, are we still meeting for coffee this weekend?"

---

## Next Steps After Testing

1. **If tests pass**: 
   - ✅ System is ready for deployment
   - ✅ Proceed with Render.com deployment (see README.md)
   - ✅ Run benchmarks for hackathon metrics

2. **If tests fail**:
   - ❌ Check troubleshooting section above
   - ❌ Review logs in terminal where `python app.py` is running
   - ❌ Test Ollama directly: `ollama run qwen2.5:7b-instruct-q5_K_M "Hello"`

---

## Continuous Testing

For ongoing development:

```powershell
# Watch mode (re-run tests on file changes)
# Install: pip install pytest-watch
ptw -- test_api.py

# Quick smoke test before commits
curl http://localhost:8000/health && python test_api.py
```

---

**Happy Testing! 🎉**
