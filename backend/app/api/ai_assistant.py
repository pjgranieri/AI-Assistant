from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB  # ensure available (Postgres)
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.deps import get_db
from app.services.summarizer import ContentSummarizer
from app.services.langchain_agent import SmartEmailProcessor

router = APIRouter()

class SummarizeRequest(BaseModel):
    content: str
    content_type: str = "general"
    metadata: Optional[Dict[str, Any]] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    use_advanced: bool = True

class SummarizeResponse(BaseModel):
    summary: str
    suggestions: Optional[List[str]] = None

class CalendarSummaryRequest(BaseModel):
    date: Optional[str] = None
    include_suggestions: bool = False

class EmailSummarizeRequest(BaseModel):
    subject: str
    content: str
    sender: Optional[str] = None

class EnhancedEmailAnalysisResponse(BaseModel):
    summary: str
    suggestions: List[str] = []
    primary_type: Optional[str] = None
    contains_event: bool = False
    contains_tasks: bool = False
    urgency: Optional[str] = None
    priority: Optional[str] = None
    event_details: Optional[Dict[str, Any]] = None
    task_details: Optional[Dict[str, Any]] = None
    recommendations: List[str] = []
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    tool_chain_used: Optional[bool] = None

@router.post("/summarize", response_model=SummarizeResponse, summary="Summarize Content")
def summarize_content(request: SummarizeRequest):
    """
    General summarization. If content_type == 'email' and use_advanced == True,
    we call the SmartEmailProcessor agent and return its summary field only
    (still can upgrade the UI to hit /ai/summarize-email for full schema).
    """
    try:
        if request.content_type == "email" and request.use_advanced:
            processor = SmartEmailProcessor()
            payload = {
                "subject": request.subject or (request.metadata or {}).get("subject", ""),
                "content": request.content,
                "sender": request.sender or (request.metadata or {}).get("sender", "")
            }
            print("[INFO] /ai/summarize -> SmartEmailProcessor (email path)")
            result = processor.process_email_with_routing(payload)
            analysis = result.get("agent_analysis", {})
            summary_text = analysis.get("summary") or analysis.get("reasoning") or ""
            # Optionally keep suggestions empty here (full endpoint returns more)
            return {"summary": summary_text, "suggestions": None}
        # legacy path
        summarizer = ContentSummarizer()
        if request.content_type == "email":
            summary = summarizer.summarize_email(request.content, request.subject or "")
            return {"summary": summary}
        else:
            suggestions = summarizer.generate_smart_suggestions(request.content)
            return {"summary": "General content processed.", "suggestions": suggestions if isinstance(suggestions, list) else [suggestions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {e}")

@router.post("/summarize-email", response_model=EnhancedEmailAnalysisResponse, summary="Summarize Email")
async def summarize_email(request: EmailSummarizeRequest, db: Session = Depends(get_db)):
    """
    Full enhanced email analysis (recommended endpoint for frontend).
    """
    processor = SmartEmailProcessor()
    legacy = ContentSummarizer()
    payload = {"subject": request.subject, "content": request.content, "sender": request.sender or ""}
    try:
        print("[INFO] /ai/summarize-email -> SmartEmailProcessor (agent)")
        result = processor.process_email_with_routing(payload)
        analysis = result.get("agent_analysis", {})
        smart_suggestions = result.get("smart_suggestions", [])
        response = {
            "summary": analysis.get("summary") or analysis.get("reasoning") or "",
            "suggestions": smart_suggestions if isinstance(smart_suggestions, list) else [smart_suggestions],
            "primary_type": analysis.get("primary_type"),
            "contains_event": analysis.get("contains_event", False),
            "contains_tasks": analysis.get("contains_tasks", False),
            "urgency": analysis.get("urgency"),
            "priority": analysis.get("priority"),
            "event_details": analysis.get("event_details"),
            "task_details": analysis.get("task_details"),
            "recommendations": analysis.get("recommendations", []),
            "confidence": analysis.get("confidence"),
            "reasoning": analysis.get("reasoning"),
            "tool_chain_used": analysis.get("tool_chain_used")
        }
        return response
    except Exception as agent_err:
        print(f"[WARN] Agent failed, fallback. Error: {agent_err}")
        try:
            legacy_summary = legacy.summarize_email(request.content, request.subject)
            legacy_suggestions = legacy.generate_smart_suggestions(f"Subject: {request.subject}\n\n{request.content}")
            return {
                "summary": legacy_summary,
                "suggestions": legacy_suggestions if isinstance(legacy_suggestions, list) else [legacy_suggestions],
                "primary_type": "informational",
                "contains_event": False,
                "contains_tasks": False,
                "urgency": "low",
                "priority": "low",
                "event_details": None,
                "task_details": None,
                "recommendations": ["no_action"],
                "confidence": 0.4,
                "reasoning": "Fallback legacy summarizer used.",
                "tool_chain_used": False
            }
        except Exception as legacy_err:
            print(f"[ERROR] Fallback failed: {legacy_err}")
            raise HTTPException(status_code=500, detail="Both agent and fallback summarizer failed.")

@router.post("/summarize-calendar", response_model=SummarizeResponse, summary="Summarize Calendar")
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