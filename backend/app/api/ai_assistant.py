from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db
from app.services.summarizer import ContentSummarizer
from app.db.models.event import Event
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime as dt

router = APIRouter()

class SummarizeRequest(BaseModel):
    content: str
    content_type: str = "general"  # email, calendar, general, daily_schedule
    metadata: Optional[Dict[str, Any]] = None

class SummarizeResponse(BaseModel):
    summary: str
    suggestions: Optional[str] = None

class EmailSummarizeRequest(BaseModel):
    subject: str
    content: str

class CalendarSummaryRequest(BaseModel):
    date: Optional[str] = None  # For daily summary
    include_suggestions: bool = True

@router.post("/ai/summarize", response_model=SummarizeResponse)
def summarize_content(request: SummarizeRequest):
    """General content summarization endpoint"""
    summarizer = ContentSummarizer()
    
    try:
        if request.content_type == "email":
            subject = request.metadata.get("subject", "") if request.metadata else ""
            summary = summarizer.summarize_email(request.content, subject)
        elif request.content_type == "general":
            summary = summarizer.generate_smart_suggestions(request.content)
        else:
            summary = summarizer.generate_smart_suggestions(request.content)
        
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@router.post("/ai/summarize-email", response_model=SummarizeResponse)
def summarize_email(request: EmailSummarizeRequest):
    """Dedicated email summarization endpoint"""
    summarizer = ContentSummarizer()
    
    try:
        summary = summarizer.summarize_email(request.content, request.subject)
        suggestions = summarizer.generate_smart_suggestions(f"Email: {request.subject}\n{request.content}")
        
        return {"summary": summary, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email summarization failed: {str(e)}")

@router.post("/ai/summarize-calendar", response_model=SummarizeResponse)
def summarize_calendar(request: CalendarSummaryRequest, db: Session = Depends(get_db)):
    """Summarize calendar events"""
    summarizer = ContentSummarizer()
    
    try:
        if request.date:
            # Get events for specific date
            target_date = dt.datetime.fromisoformat(request.date.replace('Z', '+00:00'))
            events = db.query(Event).filter(
                Event.datetime >= target_date.replace(hour=0, minute=0, second=0),
                Event.datetime < target_date.replace(hour=23, minute=59, second=59)
            ).all()
            
            events_data = [
                {
                    "title": event.title,
                    "description": event.description,
                    "datetime": event.datetime.isoformat()
                }
                for event in events
            ]
            
            summary = summarizer.summarize_daily_schedule(request.date, events_data)
        else:
            # Get all upcoming events
            events = db.query(Event).filter(Event.datetime >= dt.datetime.utcnow()).all()
            
            events_data = [
                {
                    "title": event.title,
                    "description": event.description,
                    "datetime": event.datetime.isoformat()
                }
                for event in events
            ]
            
            summary = summarizer.summarize_calendar_events(events_data)
        
        suggestions = None
        if request.include_suggestions and events_data:
            context = f"Calendar events: {summary}"
            suggestions = summarizer.generate_smart_suggestions(context)
        
        return {"summary": summary, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calendar summarization failed: {str(e)}")

@router.get("/ai/daily-brief")
def get_daily_brief(date: str = None, db: Session = Depends(get_db)):
    """Get a comprehensive daily brief"""
    summarizer = ContentSummarizer()
    
    try:
        if not date:
            date = dt.datetime.now().date().isoformat()
        
        target_date = dt.datetime.fromisoformat(date)
        
        # Get events for the day
        events = db.query(Event).filter(
            Event.datetime >= target_date.replace(hour=0, minute=0, second=0),
            Event.datetime < target_date.replace(hour=23, minute=59, second=59)
        ).all()
        
        events_data = [
            {
                "title": event.title,
                "description": event.description,
                "datetime": event.datetime.strftime("%H:%M")
            }
            for event in events
        ]
        
        if events_data:
            schedule_summary = summarizer.summarize_daily_schedule(date, events_data)
            suggestions = summarizer.generate_smart_suggestions(f"Daily schedule for {date}: {schedule_summary}")
        else:
            schedule_summary = f"No events scheduled for {date}"
            suggestions = "Consider scheduling some productive activities for the day!"
        
        return {
            "date": date,
            "events_count": len(events_data),
            "schedule_summary": schedule_summary,
            "suggestions": suggestions,
            "events": events_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Daily brief generation failed: {str(e)}")