#!/usr/bin/env python3
"""
Test script for WhatsApp OTP Service API
Usage: python test_api.py
"""

import requests
import json
import time
import sys

# Configuration
API_BASE_URL = "http://localhost:5000"  # Change this for your deployment
TEST_PHONE_NUMBER = "1234567890"  # Replace with a test number
TEST_OTP_CODE = "123456"

def test_send_otp():
    """Test sending an OTP"""
    print("🔄 Testing OTP sending...")
    
    url = f"{API_BASE_URL}/api/send-otp"
    data = {
        "phone_number": TEST_PHONE_NUMBER,
        "otp_code": TEST_OTP_CODE
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        print(f"📤 Response Status: {response.status_code}")
        print(f"📤 Response: {json.dumps(result, indent=2)}")
        
        if result.get("status") == "success":
            print("✅ OTP sending test PASSED")
            return result.get("request_id")
        else:
            print("❌ OTP sending test FAILED")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return None

def test_otp_status(request_id):
    """Test checking OTP status"""
    if not request_id:
        print("⏭️ Skipping status test (no request ID)")
        return
        
    print(f"🔄 Testing OTP status check for request: {request_id}")
    
    url = f"{API_BASE_URL}/api/otp-status/{request_id}"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        print(f"📤 Response Status: {response.status_code}")
        print(f"📤 Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            print("✅ OTP status test PASSED")
        else:
            print("❌ OTP status test FAILED")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")

def test_service_stats():
    """Test getting service statistics"""
    print("🔄 Testing service statistics...")
    
    url = f"{API_BASE_URL}/api/stats"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        print(f"📤 Response Status: {response.status_code}")
        print(f"📤 Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200 and result.get("status") == "success":
            print("✅ Service stats test PASSED")
            return result.get("stats")
        else:
            print("❌ Service stats test FAILED")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return None

def test_invalid_requests():
    """Test error handling with invalid requests"""
    print("🔄 Testing error handling...")
    
    # Test missing data
    url = f"{API_BASE_URL}/api/send-otp"
    
    test_cases = [
        # Missing phone number
        {"otp_code": "123456"},
        # Missing OTP code
        {"phone_number": "1234567890"},
        # Empty request
        {},
        # Invalid phone number
        {"phone_number": "123", "otp_code": "123456"},
        # Empty OTP
        {"phone_number": "1234567890", "otp_code": ""}
    ]
    
    for i, data in enumerate(test_cases, 1):
        print(f"🔄 Testing invalid request {i}: {data}")
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if response.status_code == 400 and result.get("status") == "error":
                print(f"✅ Invalid request {i} handled correctly")
            else:
                print(f"❌ Invalid request {i} not handled properly")
                print(f"   Status: {response.status_code}, Response: {result}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error for test {i}: {e}")

def check_service_health():
    """Check if the service is running"""
    print("🔄 Checking service health...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            result = response.json()
            stats = result.get("stats", {})
            
            print("📊 Service Health Status:")
            print(f"   🤖 Bot Running: {stats.get('bot_running', 'Unknown')}")
            print(f"   🚀 Service Running: {stats.get('service_running', 'Unknown')}")
            print(f"   📋 Queue Size: {stats.get('queue_size', 'Unknown')}")
            print(f"   📈 Total Messages: {stats.get('total_messages', 'Unknown')}")
            print(f"   ✅ Success Rate: {stats.get('successful', 0)}/{stats.get('total_messages', 0)}")
            
            return True
        else:
            print(f"❌ Service health check failed: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to service: {e}")
        print("💡 Make sure the service is running on the correct port")
        return False

def main():
    """Run all tests"""
    print("🚀 WhatsApp OTP Service API Test Suite")
    print("=" * 50)
    
    # Check service health first
    if not check_service_health():
        print("\n❌ Service appears to be down. Please start the service first.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Test service stats
    stats = test_service_stats()
    print("\n" + "-" * 30)
    
    # Test invalid requests
    test_invalid_requests()
    print("\n" + "-" * 30)
    
    # Test OTP sending
    request_id = test_send_otp()
    print("\n" + "-" * 30)
    
    # Wait a bit then test status
    if request_id:
        print("⏳ Waiting 3 seconds before checking status...")
        time.sleep(3)
        test_otp_status(request_id)
    
    print("\n" + "=" * 50)
    print("🏁 Test suite completed!")
    
    # Final stats check
    print("\n🔄 Final service stats check...")
    final_stats = test_service_stats()

if __name__ == "__main__":
    main()
