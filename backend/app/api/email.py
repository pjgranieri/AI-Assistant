from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from app.db.models.email_summary import EmailSummary
from app.deps import get_db
from pydantic import BaseModel
from typing import List, Optional
import datetime as dt

router = APIRouter()

class EmailSummaryRead(BaseModel):
    id: int
    user_id: str
    gmail_id: str
    subject: str
    sender: str
    summary: str
    sentiment: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    action_items: Optional[str] = None
    received_at: dt.datetime

    model_config = {"from_attributes": True}

class EmailSearchRequest(BaseModel):
    query: str
    limit: int = 10

@router.get("/emails", response_model=List[EmailSummaryRead])
def get_emails(
    user_id: str,
    limit: int = Query(50, le=100),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get processed emails for a user"""
    query = db.query(EmailSummary).filter(EmailSummary.user_id == user_id)
    
    if category:
        query = query.filter(EmailSummary.category == category)
    if priority:
        query = query.filter(EmailSummary.priority == priority)
    
    emails = query.order_by(desc(EmailSummary.received_at)).limit(limit).all()
    return emails

@router.post("/emails/search", response_model=List[EmailSummaryRead])
def search_emails(request: EmailSearchRequest, user_id: str, db: Session = Depends(get_db)):
    """Search emails using simple text search for now"""
    try:
        # For now, let's do a simple text search since vector search needs embeddings
        search_term = f"%{request.query}%"
        
        results = db.query(EmailSummary).filter(
            EmailSummary.user_id == user_id,
            (EmailSummary.subject.ilike(search_term) | 
             EmailSummary.summary.ilike(search_term) |
             EmailSummary.content.ilike(search_term))
        ).limit(request.limit).all()
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email search failed: {str(e)}")

@router.get("/emails/analytics/{user_id}")
def get_email_analytics(user_id: str, days: int = Query(30), db: Session = Depends(get_db)):
    """Get email analytics for a user"""
    try:
        cutoff_date = dt.datetime.utcnow() - dt.timedelta(days=days)
        
        # Get email counts by category
        category_stats = db.execute(
            text("""
                SELECT category, COUNT(*) as count
                FROM email_summaries 
                WHERE user_id = :user_id AND received_at >= :cutoff_date
                GROUP BY category
                ORDER BY count DESC
            """),
            {"user_id": user_id, "cutoff_date": cutoff_date}
        ).fetchall()
        
        # Get priority distribution
        priority_stats = db.execute(
            text("""
                SELECT priority, COUNT(*) as count
                FROM email_summaries 
                WHERE user_id = :user_id AND received_at >= :cutoff_date
                GROUP BY priority
            """),
            {"user_id": user_id, "cutoff_date": cutoff_date}
        ).fetchall()
        
        # Get sentiment distribution
        sentiment_stats = db.execute(
            text("""
                SELECT sentiment, COUNT(*) as count
                FROM email_summaries 
                WHERE user_id = :user_id AND received_at >= :cutoff_date
                GROUP BY sentiment
            """),
            {"user_id": user_id, "cutoff_date": cutoff_date}
        ).fetchall()
        
        return {
            "period_days": days,
            "categories": [{"category": row.category, "count": row.count} for row in category_stats],
            "priorities": [{"priority": row.priority, "count": row.count} for row in priority_stats],
            "sentiments": [{"sentiment": row.sentiment, "count": row.count} for row in sentiment_stats]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

@router.get("/test")
def test_endpoint():
    return {"message": "Email API is working!"}

@router.post("/emails/test-data")
def add_test_data(user_id: str = Query("test_user"), db: Session = Depends(get_db)):
    """Add test data only if user has no emails"""
    
    # Check if user already has ANY emails
    existing_count = db.query(EmailSummary).filter(EmailSummary.user_id == user_id).count()
    if existing_count > 0:
        return {
            "message": f"User {user_id} already has {existing_count} emails. Skipping test data.",
            "emails_added": 0,
            "total_emails": existing_count
        }
    
    # Create test emails only if none exist
    test_emails = [
        EmailSummary(
            user_id=user_id,
            gmail_id="test_1",
            subject="Team Meeting Tomorrow",
            sender="manager@company.com",
            recipient=f"{user_id}@company.com",
            content="Hi team, we have our weekly standup tomorrow at 10 AM. Please prepare your updates.",
            summary="Weekly team standup meeting scheduled for tomorrow at 10 AM. Team members should prepare their updates.",
            sentiment="neutral",
            priority="medium",
            category="work",
            action_items="Prepare updates for standup meeting",
            received_at=dt.datetime.utcnow() - dt.timedelta(hours=2),
            embedding=[0.1] * 1536  # Mock embedding
        ),
        EmailSummary(
            user_id=user_id,
            gmail_id="test_2",
            subject="Your Amazon order has shipped",
            sender="ship-confirm@amazon.com",
            recipient=f"{user_id}@gmail.com",
            content="Your order #123-456789 has been shipped and will arrive by Friday.",
            summary="Amazon order confirmation - package shipped, delivery expected Friday.",
            sentiment="positive",
            priority="low",
            category="personal",
            action_items="Track package delivery",
            received_at=dt.datetime.utcnow() - dt.timedelta(hours=5),
            embedding=[0.2] * 1536  # Mock embedding
        ),
        EmailSummary(
            user_id=user_id,
            gmail_id="test_3",
            subject="Special offer: 50% off premium subscription",
            sender="offers@service.com",
            recipient=f"{user_id}@gmail.com",
            content="Limited time offer! Upgrade to premium and save 50%. Offer expires in 48 hours.",
            summary="Promotional email offering 50% discount on premium subscription. Limited time offer.",
            sentiment="neutral",
            priority="medium",  # Promotional should be medium max
            category="promotional",
            action_items="Consider subscription upgrade before offer expires",
            received_at=dt.datetime.utcnow() - dt.timedelta(hours=8),
            embedding=[0.3] * 1536  # Mock embedding
        )
    ]
    
    emails_added = 0
    for email_data in test_emails:
        try:
            db.add(email_data)
            emails_added += 1
        except Exception as e:
            print(f"Error adding test email: {e}")
            continue
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error committing test data: {e}")
        return {
            "message": f"Failed to add test data: {str(e)}",
            "emails_added": 0,
            "total_emails": existing_count
        }
    
    total_count = db.query(EmailSummary).filter(EmailSummary.user_id == user_id).count()
    return {
        "message": f"Added {emails_added} test emails for {user_id}",
        "emails_added": emails_added,
        "total_emails": total_count
    }

@router.get("/emails/costs/{user_id}")
def get_processing_costs(user_id: str, db: Session = Depends(get_db)):
    """Get processing cost analytics for user"""
    
    # Get all emails for user
    emails = db.query(EmailSummary).filter(EmailSummary.user_id == user_id).all()
    
    if not emails:
        return {
            "total_cost": 0.0,
            "daily_cost": 0.0,
            "email_count": 0,
            "avg_cost_per_email": 0.0,
            "processed_today": 0
        }
    
    # Calculate costs (estimate if no processing_cost column yet)
    total_cost = 0.0
    for email in emails:
        if hasattr(email, 'processing_cost') and email.processing_cost:
            total_cost += email.processing_cost
        else:
            # Estimate cost based on content length
            content_length = len(email.content or '') + len(email.subject or '')
            estimated_cost = (content_length / 1000) * 0.002  # rough estimate
            total_cost += estimated_cost
    
    # Calculate today's costs
    today = dt.datetime.utcnow().date()
    today_emails = [e for e in emails if e.created_at.date() == today]
    daily_cost = 0.0
    for email in today_emails:
        if hasattr(email, 'processing_cost') and email.processing_cost:
            daily_cost += email.processing_cost
        else:
            content_length = len(email.content or '') + len(email.subject or '')
            estimated_cost = (content_length / 1000) * 0.002
            daily_cost += estimated_cost
    
    avg_cost = total_cost / len(emails) if emails else 0
    
    return {
        "total_cost": round(total_cost, 4),
        "daily_cost": round(daily_cost, 4),
        "email_count": len(emails),
        "avg_cost_per_email": round(avg_cost, 4),
        "processed_today": len(today_emails)
    }
