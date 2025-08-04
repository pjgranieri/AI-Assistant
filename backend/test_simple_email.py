import requests
import json

BASE_URL = "http://localhost:8000"

def test_email_system():
    print("🧪 Testing Simple Email System...")
    
    # 1. Add test data
    print("\n1. Adding test data...")
    response = requests.post(f"{BASE_URL}/api/emails/test-data")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    
    # 2. Test get emails
    print("\n2. Testing GET /api/emails")
    response = requests.get(f"{BASE_URL}/api/emails?user_id=test_user&limit=10")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        emails = response.json()
        print(f"   Found {len(emails)} emails")
        for email in emails:
            print(f"     • {email['subject']} [{email['category']}] - {email['priority']} priority")
    else:
        print(f"   Error: {response.text}")
    
    # 3. Test search emails
    print("\n3. Testing POST /api/emails/search")
    search_data = {
        "query": "report",
        "limit": 5
    }
    response = requests.post(
        f"{BASE_URL}/api/emails/search?user_id=test_user",
        json=search_data
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"   Found {len(results)} emails containing 'report'")
        for email in results:
            print(f"     • {email['subject']}")
    else:
        print(f"   Error: {response.text}")
    
    # 4. Test analytics
    print("\n4. Testing GET /api/emails/analytics")
    response = requests.get(f"{BASE_URL}/api/emails/analytics/test_user?days=30")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        analytics = response.json()
        print(f"   Analytics:")
        print(f"     Categories: {analytics['categories']}")
        print(f"     Priorities: {analytics['priorities']}")
        print(f"     Sentiments: {analytics['sentiments']}")
    else:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    test_email_system()