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
    
    # Only create test data if no emails exist
    test_emails = [
        EmailSummary(
            user_id=user_id,  # Use the provided user_id instead of hardcoded "test_user"
            gmail_id=f"{user_id}_001",  # Make gmail_id unique per user
            subject="Quarterly Report Due Tomorrow",
            sender="boss@company.com",
            recipient="you@company.com",
            content="Hi Team, Please remember that the quarterly report is due tomorrow...",
            summary="Reminder about quarterly report deadline tomorrow at 5 PM with requirements for sales figures and budget analysis.",
            sentiment="neutral",
            priority="high",
            category="work",
            action_items="• Complete quarterly report\n• Include sales figures\n• Add budget analysis",
            received_at=dt.datetime.now()
        ),
        EmailSummary(
            user_id=user_id,  # Use the provided user_id
            gmail_id=f"{user_id}_002",  # Make gmail_id unique per user
            subject="Weekend Plans - BBQ at my place!",
            sender="friend@gmail.com",
            recipient="you@gmail.com",
            content="Hey! Want to come over for a BBQ this Saturday?...",
            summary="Invitation to BBQ this Saturday at 2 PM, asking to bring side dish or drinks.",
            sentiment="positive",
            priority="low",
            category="personal",
            action_items="• Decide if attending BBQ\n• Bring side dish or drinks",
            received_at=dt.datetime.now()
        ),
        EmailSummary(
            user_id=user_id,  # Use the provided user_id
            gmail_id=f"{user_id}_003",  # Make gmail_id unique per user
            subject="🎉 50% OFF Everything - Limited Time!",
            sender="noreply@store.com",
            recipient="you@gmail.com",
            content="FLASH SALE ALERT! Get 50% off everything...",
            summary="Flash sale with 50% off everything using code FLASH50, ending at midnight.",
            sentiment="neutral",
            priority="low",
            category="promotional",
            action_items="None",
            received_at=dt.datetime.now()
        )
    ]
    
    emails_added = 0
    for email_data in test_emails:
        # Double-check each email doesn't exist
        existing = db.query(EmailSummary).filter(
            EmailSummary.gmail_id == email_data.gmail_id
        ).first()
        
        if not existing:
            db.add(email_data)
            emails_added += 1
    
    db.commit()
    
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
            "avg_cost_per_email": 0.0
        }
    
    # Calculate costs (if you add processing_cost column)
    total_cost = sum(getattr(email, 'processing_cost', 0.002) for email in emails)  # Default estimate
    
    # Calculate today's costs
    today = dt.datetime.utcnow().date()
    today_emails = [e for e in emails if e.created_at.date() == today]
    daily_cost = sum(getattr(email, 'processing_cost', 0.002) for email in today_emails)
    
    avg_cost = total_cost / len(emails) if emails else 0
    
    return {
        "total_cost": round(total_cost, 4),
        "daily_cost": round(daily_cost, 4),
        "email_count": len(emails),
        "avg_cost_per_email": round(avg_cost, 4),
        "processed_today": len(today_emails)
    }
