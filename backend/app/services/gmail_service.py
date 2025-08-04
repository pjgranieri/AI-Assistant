import os
import base64
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session
from app.db.models.user_token import UserToken
import datetime as dt
import email
from email.mime.text import MIMEText

class GmailService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.service = self._build_service()
    
    def _build_service(self):
        """Build Gmail service using stored credentials"""
        user_token = self.db.query(UserToken).filter(UserToken.user_id == self.user_id).first()
        if not user_token:
            raise ValueError("User token not found")
        
        if user_token.token_expiry and user_token.token_expiry < dt.datetime.utcnow():
            raise ValueError("Token expired")
        
        creds = Credentials(
            token=user_token.access_token,
            refresh_token=user_token.refresh_token,
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET')
        )
        
        return build('gmail', 'v1', credentials=creds)
    
    def get_messages(self, query: str = '', max_results: int = 10) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            processed_messages = []
            
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                processed_msg = self._process_message(msg_data)
                if processed_msg:
                    processed_messages.append(processed_msg)
            
            return processed_messages
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _process_message(self, msg_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single Gmail message"""
        try:
            headers = msg_data['payload'].get('headers', [])
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            to = next((h['value'] for h in headers if h['name'] == 'To'), '')
            date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Parse date
            try:
                received_at = dt.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                received_at = received_at.replace(tzinfo=None)  # Remove timezone for storage
            except:
                received_at = dt.datetime.utcnow()
            
            # Extract body
            body = self._extract_body(msg_data['payload'])
            
            return {
                'gmail_id': msg_data['id'],
                'subject': subject,
                'sender': sender,
                'recipient': to,
                'content': body,
                'received_at': received_at
            }
            
        except Exception as e:
            print(f"Error processing message: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from Gmail payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    # For now, just decode HTML (you might want to strip HTML tags)
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            if payload['body'].get('data'):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body
    
    def get_recent_emails(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get emails from the last N days"""
        query = f"newer_than:{days}d"
        return self.get_messages(query=query, max_results=50)