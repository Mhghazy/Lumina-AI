import requests
import json

# Test the backend search functionality
BASE_URL = "http://localhost:5000"

def test_search(message):
    print(f"\n{'='*60}")
    print(f"Testing: '{message}'")
    print('='*60)
    
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": message},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Status: {response.status_code}")
        print(f"\n🤖 Response:\n{data.get('response', 'No response')}")
        print(f"\n📊 Intent Data: {json.dumps(data.get('intent', {}), indent=2)}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text}")

# Test various searches
print("\n🧪 TESTING COLOR SEARCH")
test_search("show me red vendors")

print("\n\n🧪 TESTING COUNTRY SEARCH")
test_search("show me all vendors from Germany")

print("\n\n🧪 TESTING COMBINED SEARCH")
test_search("find blue vendors from Egypt")

print("\n\n🧪 TESTING COLOR VARIATION")
test_search("show me navy vendors")

print("\n\n✅ Tests Complete!")
