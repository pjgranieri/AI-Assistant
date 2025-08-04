import requests
import json

BASE_URL = "http://localhost:8000"

def test_email_endpoints():
    print("🧪 Testing Email API Endpoints...")
    
    # Test get emails
    print("\n1. Testing GET /api/emails")
    response = requests.get(f"{BASE_URL}/api/emails?user_id=test_user&limit=10")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        emails = response.json()
        print(f"   Found {len(emails)} emails")
        for email in emails[:3]:  # Show first 3
            print(f"     • {email['subject']} [{email['category']}] - {email['priority']} priority")
    
    # Test search emails
    print("\n2. Testing POST /api/emails/search")
    search_data = {
        "query": "work deadlines and reports",
        "limit": 5
    }
    response = requests.post(
        f"{BASE_URL}/api/emails/search?user_id=test_user",
        json=search_data
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"   Found {len(results)} similar emails for 'work deadlines'")
        for email in results:
            print(f"     • {email['subject']} - {email['summary'][:50]}...")
    
    # Test analytics
    print("\n3. Testing GET /api/emails/analytics")
    response = requests.get(f"{BASE_URL}/api/emails/analytics/test_user?days=30")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        analytics = response.json()
        print(f"   Analytics for last 30 days:")
        print(f"     Categories: {analytics['categories']}")
        print(f"     Priorities: {analytics['priorities']}")
        print(f"     Sentiments: {analytics['sentiments']}")

if __name__ == "__main__":
    test_email_endpoints()