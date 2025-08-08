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
    force_reprocess: bool = Query(False, description="Force reprocess existing emails"),
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
        total_cost = 0.0
        
        # Batch emails for processing
        emails_to_process = []
        
        for email_data in gmail_emails:
            # Check if we already have this email
            existing = db.query(EmailSummary).filter(
                EmailSummary.gmail_id == email_data['gmail_id'],
                EmailSummary.user_id == user_id
            ).first()
            
            if existing and not force_reprocess:
                # Check if needs reprocessing
                if not email_processor.needs_reprocessing(email_data, existing):
                    skipped_count += 1
                    continue
            
            emails_to_process.append((email_data, existing))
        
        # Process in batches to optimize API calls
        batch_size = 5
        for i in range(0, len(emails_to_process), batch_size):
            batch = emails_to_process[i:i + batch_size]
            
            for email_data, existing in batch:
                try:
                    print(f"Processing: {email_data['subject']}")
                    
                    # Calculate estimated cost
                    estimated_cost = email_processor.calculate_cost(
                        email_data['content'], "summary"
                    ) + email_processor.calculate_cost(
                        email_data['content'], "embedding"
                    )
                    
                    analysis = email_processor.process_email(email_data)
                    
                    if existing:
                        # Update existing
                        existing.summary = analysis['summary']
                        existing.embedding = analysis['embedding']
                        existing.sentiment = analysis['sentiment']
                        existing.priority = analysis['priority']
                        existing.category = analysis['category']
                        existing.action_items = analysis['action_items']
                        existing.processing_status = "processed"
                        existing.processing_cost = estimated_cost
                        existing.last_processed = dt.datetime.utcnow()
                    else:
                        # Create new
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
                            received_at=email_data['received_at'],
                            processing_status="processed",
                            processing_cost=estimated_cost,
                            last_processed=dt.datetime.utcnow()
                        )
                        db.add(email_summary)
                    
                    processed_count += 1
                    total_cost += estimated_cost
                    
                except Exception as e:
                    print(f"Error processing email {email_data['subject']}: {e}")
                    continue
            
            # Commit batch
            db.commit()
            
            # Small delay between batches to respect rate limits
            import time
            time.sleep(0.5)
        
        return {
            "message": f"Gmail sync completed",
            "fetched_count": len(gmail_emails),
            "processed_count": processed_count,
            "skipped_count": skipped_count,
            "total_cost": round(total_cost, 4),
            "emails_to_process": len(emails_to_process)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gmail sync failed: {str(e)}")