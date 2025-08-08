from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.services.gmail_service import GmailService
from app.services.email_pipeline import process_email_with_agent
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
                    
                    # Delete existing if reprocessing
                    if existing:
                        db.delete(existing)
                        db.flush()
                    
                    # Process with agent (replaces email_processor.process_email)
                    email_summary = process_email_with_agent(
                        user_id=user_id,
                        gmail_id=email_data['gmail_id'],
                        subject=email_data['subject'],
                        sender=email_data['sender'],
                        recipient=email_data.get('recipient', ''),
                        content=email_data['content'],
                        received_at=email_data['received_at']
                    )
                    
                    db.add(email_summary)
                    processed_count += 1
                    agent_used = email_summary.tool_chain_used
                    print(f"✅ Processed {'(agent)' if agent_used else '(fallback)'}")

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