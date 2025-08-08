from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.models.user_token import UserToken
from app.deps import get_db
from pydantic import BaseModel
from typing import Optional
import datetime as dt
import os
from google.auth.transport import requests
from google.oauth2 import id_token
from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse  # <-- Added this line

router = APIRouter()

# OAuth2 Configuration
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly'
    }
)

class TokenResponse(BaseModel):
    access_token: str
    user_id: str
    email: str
    expires_in: int

class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str

@router.get("/google")
async def google_auth(request: Request):
    """Initiate Google OAuth2 flow"""
    # Use the exact redirect URI that's configured in Google Console
    redirect_uri = "http://localhost:8000/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth2 callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_id = user_info['sub']
        
        # Store or update token in database
        user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
        
        if user_token:
            # Update existing token
            user_token.access_token = token['access_token']
            user_token.refresh_token = token.get('refresh_token')
            user_token.token_expiry = dt.datetime.utcnow() + dt.timedelta(seconds=token.get('expires_in', 3600))
            user_token.updated_at = dt.datetime.utcnow()
        else:
            # Create new token record
            user_token = UserToken(
                user_id=user_id,
                email=user_info['email'],
                access_token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_expiry=dt.datetime.utcnow() + dt.timedelta(seconds=token.get('expires_in', 3600))
            )
            db.add(user_token)
        
        db.commit()
        db.refresh(user_token)
        
        # 🔥 NEW: Auto-sync emails after successful authentication
        try:
            print(f"Auto-syncing emails for newly authenticated user: {user_id}")
            
            from app.services.gmail_service import GmailService
            from app.services.email_processor import EmailProcessor
            from app.db.models.email_summary import EmailSummary
            
            gmail_service = GmailService(db, user_id)
            email_processor = EmailProcessor()
            
            # Sync last 7 days of emails
            gmail_emails = gmail_service.get_recent_emails(days=7)
            processed_count = 0
            
            for email_data in gmail_emails[:10]:  # Limit to 10 emails for initial sync
                # Check if email already exists
                existing = db.query(EmailSummary).filter(
                    EmailSummary.gmail_id == email_data['gmail_id'],
                    EmailSummary.user_id == user_id
                ).first()
                
                if existing:
                    continue  # Skip if already exists
                
                try:
                    print(f"Auto-processing: {email_data['subject']}")
                    analysis = email_processor.process_email(email_data)
                    
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
                        processing_cost=0.002,  # Estimated cost
                        last_processed=dt.datetime.utcnow()
                    )
                    db.add(email_summary)
                    processed_count += 1
                    
                except Exception as e:
                    print(f"Error auto-processing email: {e}")
                    continue
            
            db.commit()
            print(f"Auto-sync completed: {processed_count} emails processed")
            
        except Exception as e:
            print(f"Auto-sync failed (non-critical): {e}")
            # Don't fail the authentication if sync fails
        
        # Redirect to frontend with user data and sync status
        frontend_redirect_url = f"http://localhost:5174/?user_id={user_id}&email={user_info['email']}&auto_synced=true"
        return RedirectResponse(url=frontend_redirect_url)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@router.get("/user/{user_id}", response_model=UserInfo)
def get_user_info(user_id: str, db: Session = Depends(get_db)):
    """Get user information"""
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if not user_token:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user_token.user_id,
        "email": user_token.email,
        "name": ""  # You can store name separately if needed
    }

@router.delete("/logout/{user_id}")
def logout_user(user_id: str, db: Session = Depends(get_db)):
    """Logout user by removing tokens"""
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if user_token:
        db.delete(user_token)
        db.commit()
    return {"message": "Successfully logged out"}

@router.get("/token/{user_id}")
def get_user_token(user_id: str, db: Session = Depends(get_db)):
    """Get user's access token (for internal use)"""
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if not user_token:
        raise HTTPException(status_code=404, detail="User token not found")

    if user_token.token_expiry and user_token.token_expiry < dt.datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")

    return {
        "access_token": user_token.access_token,
        "expires_at": user_token.token_expiry
    }
