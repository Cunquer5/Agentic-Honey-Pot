"""
Benchmark script to measure system performance.
Tests detection accuracy, latency, and extraction quality.
"""

import os
import requests
import time
import json
from typing import List, Dict, Tuple
from statistics import mean, stdev
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "your-secret-key-2026")

# Test dataset with ground truth
TEST_SCAMS = [
    {
        "message": "Sir, your SBI account is blocked. Share OTP to unblock. My UPI is scammer@paytm",
        "expected": {"banks": 0, "upis": 1, "links": 0},
        "is_scam": True
    },
    {
        "message": "Hello, visit https://fake-icici.com and enter account number 123456789012",
        "expected": {"banks": 1, "upis": 0, "links": 1},
        "is_scam": True
    },
    {
        "message": "Pay Rs 500 to winner@oksbi to claim lottery prize",
        "expected": {"banks": 0, "upis": 1, "links": 0},
        "is_scam": True
    },
    {
        "message": "Urgent: Transfer to HDFC0001234 or call https://scam-verify.net",
        "expected": {"banks": 1, "upis": 0, "links": 1},
        "is_scam": True
    },
    {
        "message": "Hi, are we still meeting for coffee tomorrow?",
        "expected": {"banks": 0, "upis": 0, "links": 0},
        "is_scam": False
    },
    {
        "message": "Your doctor's appointment is confirmed for 3 PM",
        "expected": {"banks": 0, "upis": 0, "links": 0},
        "is_scam": False
    },
]


def benchmark_detection_accuracy() -> Dict:
    """Test scam detection accuracy"""
    print("\n=== BENCHMARK: Detection Accuracy ===")
    
    results = {
        "total": len(TEST_SCAMS),
        "correct": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "latencies": []
    }
    
    for i, test in enumerate(TEST_SCAMS):
        print(f"\nTest {i+1}/{len(TEST_SCAMS)}: {test['message'][:50]}...")
        
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/webhook",
            json={
                "session_id": f"bench_detect_{i}",
                "message": test["message"]
            },
            headers={"X-API-Key": API_KEY}
        )
        latency = time.time() - start
        results["latencies"].append(latency)
        
        data = response.json()
        
        # Check if correctly identified
        detected_as_scam = not (data["done"] and data["reply"] == "")
        
        if detected_as_scam == test["is_scam"]:
            results["correct"] += 1
            print(f"✅ Correct ({latency:.2f}s)")
        else:
            if detected_as_scam and not test["is_scam"]:
                results["false_positives"] += 1
                print(f"❌ False Positive ({latency:.2f}s)")
            else:
                results["false_negatives"] += 1
                print(f"❌ False Negative ({latency:.2f}s)")
        
        time.sleep(0.5)
    
    # Calculate metrics
    accuracy = (results["correct"] / results["total"]) * 100
    avg_latency = mean(results["latencies"])
    
    print(f"\n{'='*50}")
    print(f"Detection Accuracy: {accuracy:.1f}%")
    print(f"Correct: {results['correct']}/{results['total']}")
    print(f"False Positives: {results['false_positives']}")
    print(f"False Negatives: {results['false_negatives']}")
    print(f"Average Latency: {avg_latency:.2f}s")
    print(f"{'='*50}")
    
    return results


def benchmark_extraction_quality() -> Dict:
    """Test extraction accuracy"""
    print("\n=== BENCHMARK: Extraction Quality ===")
    
    results = {
        "total_items": 0,
        "extracted_items": 0,
        "precision_scores": []
    }
    
    for i, test in enumerate(TEST_SCAMS[:4]):  # Only scam messages
        print(f"\nTest {i+1}: {test['message'][:50]}...")
        
        response = requests.post(
            f"{BASE_URL}/webhook",
            json={
                "session_id": f"bench_extract_{i}",
                "message": test["message"]
            },
            headers={"X-API-Key": API_KEY}
        )
        
        data = response.json()
        extracted = data["extracted"]
        
        # Count expected vs extracted
        expected_total = sum(test["expected"].values())
        extracted_total = len(extracted["banks"]) + len(extracted["upis"]) + len(extracted["phishing_links"])
        
        results["total_items"] += expected_total
        results["extracted_items"] += min(extracted_total, expected_total)
        
        if expected_total > 0:
            precision = min(extracted_total, expected_total) / expected_total
            results["precision_scores"].append(precision)
        
        print(f"Expected: {expected_total}, Extracted: {extracted_total}")
        print(f"  Banks: {len(extracted['banks'])}, UPIs: {len(extracted['upis'])}, Links: {len(extracted['phishing_links'])}")
        
        time.sleep(0.5)
    
    # Calculate metrics
    extraction_rate = (results["extracted_items"] / results["total_items"]) * 100 if results["total_items"] > 0 else 0
    avg_precision = mean(results["precision_scores"]) * 100 if results["precision_scores"] else 0
    
    print(f"\n{'='*50}")
    print(f"Extraction Rate: {extraction_rate:.1f}%")
    print(f"Average Precision: {avg_precision:.1f}%")
    print(f"Items Extracted: {results['extracted_items']}/{results['total_items']}")
    print(f"{'='*50}")
    
    return results


def benchmark_latency() -> Dict:
    """Test response latency under load"""
    print("\n=== BENCHMARK: Latency ===")
    
    test_message = "Sir, your account is blocked. Share OTP immediately."
    num_requests = 10
    latencies = []
    
    print(f"Sending {num_requests} requests...")
    
    for i in range(num_requests):
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/webhook",
            json={
                "session_id": f"bench_latency_{i}",
                "message": test_message
            },
            headers={"X-API-Key": API_KEY}
        )
        latency = time.time() - start
        latencies.append(latency)
        
        print(f"  Request {i+1}: {latency:.2f}s")
        time.sleep(0.5)
    
    # Calculate statistics
    avg_latency = mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    std_latency = stdev(latencies) if len(latencies) > 1 else 0
    
    print(f"\n{'='*50}")
    print(f"Average Latency: {avg_latency:.2f}s")
    print(f"Min Latency: {min_latency:.2f}s")
    print(f"Max Latency: {max_latency:.2f}s")
    print(f"Std Dev: {std_latency:.2f}s")
    print(f"{'='*50}")
    
    return {
        "avg": avg_latency,
        "min": min_latency,
        "max": max_latency,
        "std": std_latency
    }


def run_benchmarks():
    """Run all benchmarks"""
    print("=" * 60)
    print("AGENTIC HONEY-POT BENCHMARK SUITE")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server not responding. Is it running?")
            return
    except:
        print("❌ Cannot connect to server. Is it running at", BASE_URL, "?")
        return
    
    # Run benchmarks
    detection_results = benchmark_detection_accuracy()
    extraction_results = benchmark_extraction_quality()
    latency_results = benchmark_latency()
    
    # Final summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"\n✅ Detection Accuracy: {(detection_results['correct']/detection_results['total']*100):.1f}%")
    print(f"✅ Extraction Rate: {(extraction_results['extracted_items']/extraction_results['total_items']*100):.1f}%")
    print(f"✅ Average Latency: {latency_results['avg']:.2f}s")
    
    # Evaluation against targets
    print(f"\n📊 Hackathon Evaluation Metrics:")
    print(f"  Detection Accuracy: {(detection_results['correct']/detection_results['total']*100):.1f}% (Target: >90%)")
    print(f"  Extraction Completeness: {(extraction_results['extracted_items']/extraction_results['total_items']*100):.1f}% (Target: >70%)")
    print(f"  Response Latency: {latency_results['avg']:.2f}s (Target: <5s)")
    print(f"  False Positives: {detection_results['false_positives']} (Target: <5%)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_benchmarks()
