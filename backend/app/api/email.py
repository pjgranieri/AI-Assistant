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
def add_test_data(db: Session = Depends(get_db)):
    """Add some test email data"""
    test_emails = [
        EmailSummary(
            user_id="test_user",
            gmail_id="test_001",
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
            user_id="test_user",
            gmail_id="test_002",
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
            user_id="test_user",
            gmail_id="test_003",
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
    
    for email in test_emails:
        # Check if already exists
        existing = db.query(EmailSummary).filter(EmailSummary.gmail_id == email.gmail_id).first()
        if not existing:
            db.add(email)
    
    db.commit()
    
    count = db.query(EmailSummary).filter(EmailSummary.user_id == "test_user").count()
    return {"message": f"Test data added. Total emails for test_user: {count}"}
