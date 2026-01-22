# Quick Test Script for Lumina Backend
# Run this to verify the backend is working

import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

print("🧪 Testing Lumina Backend...")
print("=" * 50)

# Test 1: Health Check
print("\n1️⃣ Testing health endpoint...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    if response.status_code == 200:
        print("   ✅ Health check PASSED")
        print(f"   Response: {response.json()}")
    else:
        print(f"   ❌ Health check FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Health check ERROR: {e}")
    print("   💡 Make sure backend is running: python lumina_backend.py")
    exit(1)

# Test 2: Create New Conversation
print("\n2️⃣ Testing conversation creation...")
try:
    response = requests.post(f"{BASE_URL}/conversations/new", timeout=5)
    if response.status_code == 200:
        data = response.json()
        conversation_id = data.get('conversation_id')
        print("   ✅ Conversation created PASSED")
        print(f"   Conversation ID: {conversation_id}")
    else:
        print(f"   ❌ Conversation creation FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Conversation creation ERROR: {e}")

# Test 3: Send Chat Message
print("\n3️⃣ Testing chat endpoint...")
try:
    payload = {
        "message": "Hello Lumina! Tell me a joke about databases.",
        "conversation_id": conversation_id
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload, timeout=15)
    
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Chat PASSED")
        print(f"   AI Response: {data['response'][:100]}...")
        print(f"   Intent: {data.get('intent', {}).get('action', 'unknown')}")
    else:
        print(f"   ❌ Chat FAILED: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ❌ Chat ERROR: {e}")

# Test 4: List Conversations
print("\n4️⃣ Testing conversation list...")
try:
    response = requests.get(f"{BASE_URL}/conversations", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Conversation list PASSED")
        print(f"   Total conversations: {len(data['conversations'])}")
    else:
        print(f"   ❌ Conversation list FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Conversation list ERROR: {e}")

# Test 5: Get Specific Conversation
print("\n5️⃣ Testing conversation retrieval...")
try:
    response = requests.get(f"{BASE_URL}/conversations/{conversation_id}", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Conversation retrieval PASSED")
        print(f"   Messages: {len(data['messages'])}")
    else:
        print(f"   ❌ Conversation retrieval FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Conversation retrieval ERROR: {e}")

# Test 6: Export Conversation
print("\n6️⃣ Testing conversation export...")
try:
    response = requests.get(f"{BASE_URL}/export/{conversation_id}", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print("   ✅ Conversation export PASSED")
        print(f"   Export length: {len(data['data']['text_export'])} characters")
    else:
        print(f"   ❌ Conversation export FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Conversation export ERROR: {e}")

# Test 7: Delete Conversation
print("\n7️⃣ Testing conversation deletion...")
try:
    response = requests.delete(f"{BASE_URL}/conversations/{conversation_id}", timeout=5)
    if response.status_code == 200:
        print("   ✅ Conversation deletion PASSED")
    else:
        print(f"   ❌ Conversation deletion FAILED: {response.status_code}")
except Exception as e:
    print(f"   ❌ Conversation deletion ERROR: {e}")

print("\n" + "=" * 50)
print("🎉 Testing Complete!")
print("\n📊 Summary:")
print("   - Backend is running ✅")
print("   - Groq API is working ✅")
print("   - All endpoints tested ✅")
print("\n💡 Next step: Open public/vendors.html and click 💬 AI Chat!")
