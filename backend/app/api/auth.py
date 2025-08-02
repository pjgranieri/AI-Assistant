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

@router.get("/auth/google")
async def google_auth(request: Request):
    """Initiate Google OAuth2 flow"""
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth2 callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        # Store or update token in database
        user_token = db.query(UserToken).filter(UserToken.user_id == user_info['sub']).first()
        
        if user_token:
            # Update existing token
            user_token.access_token = token['access_token']
            user_token.refresh_token = token.get('refresh_token')
            user_token.token_expiry = dt.datetime.utcnow() + dt.timedelta(seconds=token.get('expires_in', 3600))
            user_token.updated_at = dt.datetime.utcnow()
        else:
            # Create new token record
            user_token = UserToken(
                user_id=user_info['sub'],
                email=user_info['email'],
                access_token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_expiry=dt.datetime.utcnow() + dt.timedelta(seconds=token.get('expires_in', 3600))
            )
            db.add(user_token)
        
        db.commit()
        db.refresh(user_token)
        
        # Redirect to frontend with user data - UPDATE PORT HERE
        frontend_redirect_url = f"http://localhost:5174/?user_id={user_info['sub']}&email={user_info['email']}"
        return RedirectResponse(url=frontend_redirect_url)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@router.get("/auth/user/{user_id}", response_model=UserInfo)
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

@router.delete("/auth/logout/{user_id}")
def logout_user(user_id: str, db: Session = Depends(get_db)):
    """Logout user by removing tokens"""
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if user_token:
        db.delete(user_token)
        db.commit()
    return {"message": "Successfully logged out"}

@router.get("/auth/token/{user_id}")
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
