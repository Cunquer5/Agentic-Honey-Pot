"""
Simple mock scammer simulator for local testing.
Simulates the Mock Scammer API behavior.
"""

import random
from typing import List, Dict

class MockScammer:
    """Simulates scammer behavior for testing"""
    
    INITIAL_SCAMS = [
        "Hello sir, this is State Bank of India. Your account shows suspicious activity. Please verify your details immediately.",
        "Congratulations! You won Rs 50,000 in lucky draw. Pay Rs 500 processing fee to claim.",
        "Dear customer, your KYC is expired. Click link to update: https://fake-bank-verify.com",
        "Sir I am calling from Income Tax department. You have pending tax of Rs 25,000. Pay immediately to avoid arrest.",
        "Hello, your parcel is stuck at customs. Pay Rs 1,500 clearance fee to release.",
    ]
    
    FOLLOW_UPS = {
        "account": [
            "Sir, what is your account number? I need to verify.",
            "Please share your bank account details for refund processing.",
            "Sir, tell me your IFSC code and account number.",
        ],
        "upi": [
            "Sir, send Rs 1 to my UPI to verify: scammer@paytm",
            "Please pay to verify@oksbi for confirmation.",
            "Send small amount to test123@ybl for processing.",
        ],
        "link": [
            "Sir, visit this link to complete: https://fake-verify-portal.com",
            "Click here to update details: https://scam-kyc-update.net",
            "Go to https://fake-refund-claim.com and enter OTP",
        ],
        "otp": [
            "Sir, what is the OTP you received on mobile?",
            "Please share the 6-digit code from SMS.",
            "Tell me the verification code to proceed.",
        ],
        "pressure": [
            "Sir, your account will be blocked in 24 hours if you don't act now!",
            "This is urgent sir, police case will be filed!",
            "Sir, you will lose Rs 50,000 if you don't pay today!",
        ],
        "closing": [
            "Thank you sir, your issue is resolved.",
            "Ok sir, we will process this and call you back.",
            "Alright sir, have a nice day.",
        ]
    }
    
    def __init__(self):
        self.conversation_state = "initial"
        self.turn_count = 0
    
    def get_initial_message(self) -> str:
        """Get random initial scam message"""
        return random.choice(self.INITIAL_SCAMS)
    
    def get_next_message(self, agent_reply: str) -> str:
        """
        Generate next scammer message based on agent's reply.
        Simple state machine for realistic flow.
        """
        self.turn_count += 1
        agent_lower = agent_reply.lower()
        
        # If agent is ending conversation
        if any(word in agent_lower for word in ["bye", "thank", "later", "thik hai"]):
            return random.choice(self.FOLLOW_UPS["closing"])
        
        # If agent asks about payment method
        if any(word in agent_lower for word in ["pay", "send", "account", "upi"]):
            if self.turn_count % 2 == 0:
                return random.choice(self.FOLLOW_UPS["upi"])
            else:
                return random.choice(self.FOLLOW_UPS["account"])
        
        # If agent asks about website/link
        if any(word in agent_lower for word in ["link", "website", "where", "kahan"]):
            return random.choice(self.FOLLOW_UPS["link"])
        
        # If agent seems confused (good for extraction)
        if any(word in agent_lower for word in ["confused", "samajh", "understand", "kya"]):
            # Provide more details
            if self.turn_count <= 2:
                return random.choice(self.FOLLOW_UPS["account"])
            elif self.turn_count <= 4:
                return random.choice(self.FOLLOW_UPS["upi"])
            else:
                return random.choice(self.FOLLOW_UPS["link"])
        
        # Default: escalate pressure
        if self.turn_count >= 5:
            return random.choice(self.FOLLOW_UPS["closing"])
        else:
            return random.choice(self.FOLLOW_UPS["pressure"])
    
    def reset(self):
        """Reset conversation state"""
        self.conversation_state = "initial"
        self.turn_count = 0


def simulate_conversation(api_url: str, api_key: str, max_turns: int = 10):
    """
    Simulate a full scam conversation with the honey-pot API.
    """
    import requests
    import time
    
    scammer = MockScammer()
    session_id = f"sim_{int(time.time())}"
    
    print(f"\n{'='*60}")
    print(f"SIMULATED SCAM CONVERSATION")
    print(f"Session ID: {session_id}")
    print(f"{'='*60}\n")
    
    # Initial message
    current_message = scammer.get_initial_message()
    
    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")
        print(f"🔴 Scammer: {current_message}")
        
        # Send to API
        try:
            response = requests.post(
                f"{api_url}/webhook",
                json={
                    "session_id": session_id,
                    "message": current_message
                },
                headers={"X-API-Key": api_key},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                print(response.text)
                break
            
            data = response.json()
            agent_reply = data["reply"]
            extracted = data["extracted"]
            done = data["done"]
            
            print(f"🟢 Agent: {agent_reply}")
            
            if extracted["banks"] or extracted["upis"] or extracted["phishing_links"]:
                print(f"📊 Extracted:")
                if extracted["banks"]:
                    print(f"   Banks: {extracted['banks']}")
                if extracted["upis"]:
                    print(f"   UPIs: {extracted['upis']}")
                if extracted["phishing_links"]:
                    print(f"   Links: {extracted['phishing_links']}")
            
            if done:
                print(f"\n✅ Conversation ended by agent")
                break
            
            # Generate next scammer message
            current_message = scammer.get_next_message(agent_reply)
            
            time.sleep(1)  # Rate limiting
            
        except requests.exceptions.Timeout:
            print(f"⏱️ Request timeout (LLM might be slow)")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            break
    
    # Get final metrics
    print(f"\n{'='*60}")
    print(f"CONVERSATION SUMMARY")
    print(f"{'='*60}")
    
    try:
        metrics_response = requests.get(
            f"{api_url}/metrics/{session_id}",
            headers={"X-API-Key": api_key}
        )
        
        if metrics_response.status_code == 200:
            metrics = metrics_response.json()
            print(f"\nTotal turns: {metrics['turn_count']}")
            print(f"Duration: {metrics['duration_seconds']:.1f}s")
            print(f"Detected as scam: {metrics['detected_scam']}")
            print(f"\nFinal extracted intelligence:")
            print(f"  Banks: {metrics['extracted_info']['banks']}")
            print(f"  UPIs: {metrics['extracted_info']['upis']}")
            print(f"  Phishing links: {metrics['extracted_info']['phishing_links']}")
    except Exception as e:
        print(f"Could not fetch metrics: {e}")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run simulation
    simulate_conversation(
        api_url=os.getenv("BASE_URL", "https://Conquerer55555-Agentic-honey-pot.hf.space"),
        api_key=os.getenv("API_KEY", "your-secret-key-2026"),
        max_turns=10
    )
