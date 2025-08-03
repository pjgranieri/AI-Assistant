import dotenv
dotenv.load_dotenv()

import sys
sys.path.append('.')

from app.services.email_processor import EmailProcessor
from app.db.session import get_db
from app.db.models.email_summary import EmailSummary
import datetime as dt

# Test email data
test_emails = [
    {
        'gmail_id': 'test_001',
        'subject': 'Quarterly Report Due Tomorrow',
        'sender': 'boss@company.com',
        'recipient': 'you@company.com',
        'content': '''Hi Team,

Please remember that the quarterly report is due tomorrow by 5 PM. 
We need to include:
- Sales figures for Q3
- Budget analysis
- Next quarter projections

This is critical for our board meeting on Friday. Let me know if you need any help.

Best regards,
Manager''',
        'received_at': dt.datetime.now()
    },
    {
        'gmail_id': 'test_002',
        'subject': 'Weekend Plans - BBQ at my place!',
        'sender': 'friend@gmail.com',
        'recipient': 'you@gmail.com',
        'content': '''Hey!

Want to come over for a BBQ this Saturday? Starting around 2 PM.
Bringing some burgers, hot dogs, and veggie options.
Feel free to bring a side dish or drinks!

Let me know if you can make it.

Cheers,
Alex''',
        'received_at': dt.datetime.now()
    },
    {
        'gmail_id': 'test_003',
        'subject': '🎉 50% OFF Everything - Limited Time!',
        'sender': 'noreply@store.com',
        'recipient': 'you@gmail.com',
        'content': '''FLASH SALE ALERT!

Get 50% off everything in our store for the next 24 hours only!
Use code: FLASH50

Shop now for:
- Electronics
- Clothing
- Home & Garden
- Sports equipment

Sale ends midnight tonight. Don't miss out!

Happy shopping!''',
        'received_at': dt.datetime.now()
    }
]

def test_email_processing():
    print("🧪 Testing Email Processing...")
    
    # Initialize processor
    processor = EmailProcessor()
    
    # Get database session
    db = next(get_db())
    
    try:
        for email_data in test_emails:
            print(f"\n📧 Processing: {email_data['subject']}")
            
            # Process email with AI
            analysis = processor.process_email(email_data)
            
            print(f"   Summary: {analysis['summary']}")
            print(f"   Category: {analysis['category']}")
            print(f"   Priority: {analysis['priority']}")
            print(f"   Sentiment: {analysis['sentiment']}")
            print(f"   Action Items: {analysis['action_items']}")
            print(f"   Embedding dimensions: {len(analysis['embedding'])}")
            
            # Save to database
            email_summary = EmailSummary(
                user_id='test_user',
                gmail_id=email_data['gmail_id'],
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipient=email_data['recipient'],
                content=email_data['content'],
                summary=analysis['summary'],
                embedding=analysis['embedding'],
                sentiment=analysis['sentiment'],
                priority=analysis['priority'],
                category=analysis['category'],
                action_items=analysis['action_items'],
                received_at=email_data['received_at']
            )
            
            db.add(email_summary)
        
        db.commit()
        print("\n✅ All emails processed and saved to database!")
        
        # Test similarity search
        print("\n🔍 Testing similarity search...")
        test_queries = [
            "work reports and deadlines",
            "social events and parties",
            "shopping and discounts"
        ]
        
        for query in test_queries:
            print(f"\n Query: '{query}'")
            query_embedding = processor.generate_embedding(query)
            
            # Get all embeddings from database for comparison
            all_emails = db.query(EmailSummary).filter(EmailSummary.user_id == 'test_user').all()
            
            similarities = []
            for email in all_emails:
                if email.embedding:
                    # Calculate cosine similarity
                    import numpy as np
                    similarity = np.dot(query_embedding, email.embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(email.embedding)
                    )
                    similarities.append((email.subject, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            print("   Most similar emails:")
            for subject, score in similarities[:3]:
                print(f"     • {subject} (score: {score:.3f})")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_email_processing()