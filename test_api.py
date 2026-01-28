"""
Test script for Agentic Honey-Pot API
Simulates scam conversations and validates responses.
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
BASE_URL = "http://localhost:8000"

import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("API_KEY", "your-secret-key-2026")

# Test scam messages (Indian context)
SCAM_MESSAGES = [
    # Bank impersonation
    "Hello sir, this is from State Bank of India. Your ATM card is blocked due to suspicious activity. Please share your card number and CVV to unblock immediately.",
    
    # UPI scam
    "Congratulations! You have won Rs 50,000 in Google Pay lucky draw. Send Rs 500 processing fee to winner@paytm to claim your prize.",
    
    # Phishing link
    "Dear customer, your account will be suspended. Click https://fake-icici-login.com/verify to update KYC details urgently.",
    
    # OTP scam
    "This is HDFC Bank security. We detected unauthorized transaction of Rs 25,000. Share the OTP sent to your mobile to block this transaction.",
    
    # Investment scam
    "Sir, I am calling from Stock Market Advisory. Invest Rs 10,000 in our scheme and get 300% returns in 30 days. Send money to invest@oksbi.",
]

NON_SCAM_MESSAGES = [
    "Hi, I'm calling about the apartment you listed for rent. Is it still available?",
    "Hello, this is a reminder about your doctor's appointment tomorrow at 3 PM.",
    "Hey, are we still meeting for coffee this weekend?",
]


def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_scam_conversation(initial_message: str, session_id: str = None) -> Dict:
    """Test a full scam conversation"""
    if not session_id:
        session_id = f"test_{int(time.time())}"
    
    print(f"\n=== Testing Scam Conversation ===")
    print(f"Session ID: {session_id}")
    print(f"Initial message: {initial_message[:80]}...")
    
    conversation_log = []
    turn = 0
    max_turns = 10
    
    current_message = initial_message
    
    while turn < max_turns:
        print(f"\n--- Turn {turn + 1} ---")
        print(f"Scammer: {current_message}")
        
        # Send webhook request
        response = requests.post(
            f"{BASE_URL}/webhook",
            json={
                "session_id": session_id,
                "message": current_message
            },
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            break
        
        data = response.json()
        conversation_log.append({
            "turn": turn + 1,
            "scammer": current_message,
            "agent": data["reply"],
            "extracted": data["extracted"],
            "done": data["done"]
        })
        
        print(f"Agent: {data['reply']}")
        print(f"Extracted: {data['extracted']}")
        print(f"Done: {data['done']}")
        
        if data["done"]:
            print("\n✓ Conversation ended")
            break
        
        # Simulate scammer's next message (for demo, just acknowledge)
        # In real scenario, this would come from Mock Scammer API
        if turn == 0:
            current_message = "Yes sir, I need your account number to process the refund. What is your account number?"
        elif turn == 1:
            current_message = "Sir, please send small amount to verify your account. My UPI is scammer@paytm"
        elif turn == 2:
            current_message = "Thank you sir. Also visit https://fake-bank.com/verify to complete verification."
        else:
            current_message = "Ok sir, thank you for your cooperation."
        
        turn += 1
        time.sleep(1)  # Rate limiting
    
    return {
        "session_id": session_id,
        "total_turns": turn + 1,
        "conversation_log": conversation_log
    }


def test_metrics(session_id: str):
    """Test metrics endpoint"""
    print(f"\n=== Testing Metrics Endpoint ===")
    print(f"Session ID: {session_id}")
    
    response = requests.get(
        f"{BASE_URL}/metrics/{session_id}",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        metrics = response.json()
        print(f"\nMetrics:")
        print(f"  Detected as scam: {metrics['detected_scam']}")
        print(f"  Total turns: {metrics['turn_count']}")
        print(f"  Duration: {metrics['duration_seconds']:.2f}s")
        print(f"  Extracted info:")
        print(f"    Banks: {metrics['extracted_info']['banks']}")
        print(f"    UPIs: {metrics['extracted_info']['upis']}")
        print(f"    Links: {metrics['extracted_info']['phishing_links']}")
        return metrics
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def test_non_scam_detection():
    """Test that non-scam messages are correctly rejected"""
    print("\n=== Testing Non-Scam Detection ===")
    
    for msg in NON_SCAM_MESSAGES[:2]:  # Test first 2
        print(f"\nMessage: {msg}")
        response = requests.post(
            f"{BASE_URL}/webhook",
            json={
                "session_id": f"nonscam_{int(time.time())}",
                "message": msg
            },
            headers={"X-API-Key": API_KEY}
        )
        
        data = response.json()
        print(f"Done immediately: {data['done']}")
        print(f"Reply: '{data['reply']}'")
        
        if data['done'] and data['reply'] == "":
            print("✓ Correctly identified as non-scam")
        else:
            print("✗ False positive - treated as scam")
        
        time.sleep(1)


def test_authentication():
    """Test API key authentication"""
    print("\n=== Testing Authentication ===")
    
    # Test without API key
    response = requests.post(
        f"{BASE_URL}/webhook",
        json={
            "session_id": "test",
            "message": "test"
        }
    )
    print(f"Without API key: {response.status_code} (expected 401)")
    
    # Test with wrong API key
    response = requests.post(
        f"{BASE_URL}/webhook",
        json={
            "session_id": "test",
            "message": "test"
        },
        headers={"X-API-Key": "wrong-key"}
    )
    print(f"With wrong API key: {response.status_code} (expected 401)")
    
    # Test with correct API key
    response = requests.post(
        f"{BASE_URL}/webhook",
        json={
            "session_id": "test_auth",
            "message": "Hello"
        },
        headers={"X-API-Key": API_KEY}
    )
    print(f"With correct API key: {response.status_code} (expected 200)")


def run_all_tests():
    """Run all test cases"""
    print("=" * 60)
    print("AGENTIC HONEY-POT API TEST SUITE")
    print("=" * 60)
    
    # Health check
    if not test_health():
        print("\n✗ Health check failed. Is the server running?")
        return
    
    # Authentication
    test_authentication()
    
    # Non-scam detection
    test_non_scam_detection()
    
    # Full scam conversation
    result = test_scam_conversation(SCAM_MESSAGES[0])
    
    # Get metrics
    if result:
        test_metrics(result["session_id"])
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
