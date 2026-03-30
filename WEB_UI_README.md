# Scammer Roleplay Web UI

A modern web interface for interacting with the Agentic Honey-Pot system, allowing users to roleplay as scammers while the LLM extracts intelligence data in real-time.

## Features

- **Real-time Chat Interface**: Interactive chat with the Ramesh Patel AI persona
- **Intelligence Extraction Panel**: Live display of extracted data including:
  - Bank accounts and IFSC codes
  - UPI IDs
  - Phone numbers
  - Phishing links
  - Suspicious keywords
- **Session Management**: Track conversation turns and scam detection status
- **Modern UI**: Built with TailwindCSS and Alpine.js for responsive design
- **Real-time Updates**: Automatic intelligence extraction display
~
## Quick Start

### Prerequisites

1. **Ollama Installation**: Make sure Ollama is installed and running
   ```bash
   # Install and run Ollama
   ollama serve
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the FastAPI Server**:
   ```bash
   python app.py
   ```
   The server will start on `http://localhost:7860`

2. **Open the Web UI**:
   Navigate to `http://localhost:7860` in your browser

### Alternative: Using Docker

```bash
# Build and run with Docker
docker build -t agentic-honey-pot .
docker run -p 7860:7860 agentic-honey-pot
```

## Using the Web Interface

### Chat Interface
- **Roleplay as a scammer**: Type messages in the input field
- **View AI responses**: The system responds as "Ramesh Patel" - a confused but helpful retired man
- **Real-time processing**: Messages are processed instantly with typing indicators

### Intelligence Panel
The right sidebar displays extracted intelligence in real-time:

- **Session Stats**: Turn count and scam detection status
- **Bank Accounts**: Detected account numbers and IFSC codes
- **UPI IDs**: Extracted UPI payment identifiers
- **Phone Numbers**: Indian phone numbers (+91 format)
- **Phishing Links**: Suspicious URLs
- **Suspicious Keywords**: Alert words like "urgent", "verify", "blocked", etc.

### Session Management
- **Reset Session**: Clear conversation history and start fresh
- **Session ID**: Unique identifier for each conversation
- **Status Indicator**: Shows current system state

## API Endpoints

The web UI uses these backend endpoints:

- `GET /` - Web UI interface
- `POST /webhook` - Main chat processing
- `GET /metrics/{sessionId}` - Session intelligence data
- `GET /health` - System health check
- `GET /api` - API information
- `DELETE /sessions/{sessionId}` - Session cleanup

## Configuration

Environment variables in `.env`:

```bash
API_KEY=your-secret-key-2026
OLLAMA_MODEL=llama3.2:1b-instruct-q4_K_M
OLLAMA_HOST=localhost:11434
MAX_TURNS=15
```

## Example Scammer Messages to Try

- "Your account has been blocked. Click here to verify: http://fake-bank.com/verify"
- "Send money to this UPI: victim@oksbi for prize claim"
- "Call +919876543210 immediately for ATM card issue"
- "Your KYC is incomplete. Share OTP 123456"

## Technical Details

### Frontend Technologies
- **TailwindCSS**: Modern styling framework
- **Alpine.js**: Lightweight reactive JavaScript
- **Vanilla JS**: WebSocket support and API communication

### Backend Integration
- **FastAPI**: Web framework with static file serving
- **Jinja2**: Template engine for HTML rendering
- **CORS**: Enabled for cross-origin requests

### Intelligence Extraction
The system uses regex patterns to extract:
- UPI IDs: `user@bank` format
- Bank accounts: 9-18 digits and IFSC codes
- Phone numbers: Indian format with +91 prefix
- URLs: HTTP/HTTPS links
- Keywords: Suspicious vocabulary matching

## Troubleshooting

### Common Issues

1. **Ollama Connection Error**:
   - Ensure Ollama is running: `ollama serve`
   - Check model availability: `ollama list`

2. **CORS Issues**:
   - The app has CORS enabled for all origins
   - Check if other services are using the same port

3. **Static Files Not Loading**:
   - Verify `templates/` directory exists
   - Check file permissions

4. **Slow Response Times**:
   - Check Ollama model size
   - Monitor system resources
   - Consider smaller models for faster responses

### Debug Mode

Enable debug logging:
```bash
export DEBUG=true
python app.py
```

## Development

### Adding New Features

1. **Frontend**: Modify `templates/index.html`
2. **Backend**: Update `app.py` endpoints
3. **Styling**: Edit Tailwind classes in HTML
4. **JavaScript**: Add scripts in HTML or separate files

### WebSocket Enhancement (Optional)

The system includes optional WebSocket support for real-time updates:
- File: `static/js/websocket.js`
- Uncomment and implement WebSocket endpoints in `app.py`

## Security Notes

- Default API key is for development only
- Change `API_KEY` in production
- The system extracts sensitive information - use responsibly
- All data is stored in memory only (no persistence)

## License

This project is part of the Agentic Honey-Pot system for scam detection and research purposes.
