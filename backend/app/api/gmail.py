from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services.gmail_service import GmailService
from app.services.email_processor import EmailProcessor
from app.db.models.email_summary import EmailSummary
from app.db.models.user_token import UserToken
from app.deps import get_db
import datetime as dt

router = APIRouter()

@router.get("/gmail/status")
def get_gmail_status(user_id: str, db: Session = Depends(get_db)):
    """Check if user has connected Gmail"""
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    
    if not user_token:
        return {"connected": False, "message": "No token found"}
    
    # Check if token is still valid
    if user_token.token_expiry and user_token.token_expiry < dt.datetime.utcnow():
        return {"connected": False, "message": "Token expired"}
    
    return {"connected": True, "message": "Gmail connected"}

@router.post("/gmail/sync")
def sync_gmail_emails(
    user_id: str, 
    days: int = Query(7, description="Number of days to sync"), 
    db: Session = Depends(get_db)
):
    """Sync recent emails from Gmail and process with AI"""
    try:
        # Initialize services
        gmail_service = GmailService(db, user_id)
        email_processor = EmailProcessor()
        
        # Fetch recent emails from Gmail
        print(f"Fetching emails from last {days} days for user {user_id}")
        gmail_emails = gmail_service.get_recent_emails(days=days)
        
        processed_count = 0
        skipped_count = 0
        
        for email_data in gmail_emails:
            # Check if we already have this email
            existing = db.query(EmailSummary).filter(
                EmailSummary.gmail_id == email_data['gmail_id'],
                EmailSummary.user_id == user_id
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            print(f"Processing new email: {email_data['subject']}")
            
            # Process with AI
            try:
                analysis = email_processor.process_email(email_data)
                
                # Save to database
                email_summary = EmailSummary(
                    user_id=user_id,
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
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing email {email_data['subject']}: {e}")
                continue
        
        db.commit()
        
        return {
            "message": f"Gmail sync completed",
            "fetched_count": len(gmail_emails),
            "processed_count": processed_count,
            "skipped_count": skipped_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gmail sync failed: {str(e)}")