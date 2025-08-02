from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models.email_summary import EmailSummary
from app.deps import get_db
from pydantic import BaseModel
import datetime

from app.services.summarizer import summarize_text

router = APIRouter()

class EmailSummaryCreate(BaseModel):
    user_id: int
    subject: str
    summary: str
    received_at: datetime.datetime = None

class EmailSummaryRead(BaseModel):
    id: int
    user_id: int
    subject: str
    summary: str
    received_at: datetime.datetime

    class Config:
        orm_mode = True

@router.post("/summarize-email", response_model=EmailSummaryRead)
def summarize_email(email: EmailSummaryCreate, db: Session = Depends(get_db)):
    db_email = EmailSummary(
        user_id=email.user_id,
        subject=email.subject,
        summary=email.summary,
        received_at=email.received_at or datetime.datetime.utcnow()
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email

class SummarizeRequest(BaseModel):
    text: str

class SummarizeResponse(BaseModel):
    summary: str

@router.post("/summarize", response_model=SummarizeResponse)
def summarize(req: SummarizeRequest):
    summary = summarize_text(req.text)
    return {"summary": summary}