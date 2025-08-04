from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models.event import Event
from app.deps import get_db
from pydantic import BaseModel
from typing import List, Optional
import datetime as dt

router = APIRouter()

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    datetime: Optional[str] = None  # Change to string to handle local time

class EventRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    datetime: dt.datetime

    model_config = {"from_attributes": True}

class SettingsUpdate(BaseModel):
    timezone: Optional[str] = None
    use_24h_format: Optional[bool] = None

@router.post("/events", response_model=EventRead)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    # Parse the datetime string as local time
    if event.datetime:
        try:
            # Parse the string as local time (no timezone conversion)
            event_datetime = dt.datetime.fromisoformat(event.datetime.replace('Z', ''))
            print(f"Parsed datetime as local time: {event_datetime}")
        except ValueError:
            # Fallback to current time if parsing fails
            event_datetime = dt.datetime.now()
            print(f"Failed to parse datetime, using current time: {event_datetime}")
    else:
        event_datetime = dt.datetime.now()
    
    print(f"Creating event: {event.title}")
    print(f"Received datetime string: {event.datetime}")
    print(f"Storing datetime: {event_datetime}")
    
    db_event = Event(
        title=event.title,
        description=event.description,
        datetime=event_datetime
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return db_event

@router.get("/events", response_model=List[EventRead])
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).all()

@router.put("/events/{event_id}", response_model=EventRead)
def update_event(event_id: int, event: EventCreate, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    db_event.title = event.title
    db_event.description = event.description
    if event.datetime:
        try:
            event_datetime = dt.datetime.fromisoformat(event.datetime.replace('Z', ''))
            db_event.datetime = event_datetime
        except ValueError:
            pass  # Keep existing datetime if parsing fails
        
    db.commit()
    db.refresh(db_event)
    return db_event

@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(db_event)
    db.commit()
    return

# Clear all events
@router.delete("/events", status_code=204)
def clear_all_events(db: Session = Depends(get_db)):
    """Clear all events from the calendar"""
    deleted_count = db.query(Event).delete()
    db.commit()
    print(f"Cleared {deleted_count} events from calendar")
    return

# Get available timezones
@router.get("/timezones")
def get_timezones():
    """Get list of common timezones"""
    common_timezones = [
        {"value": "US/Eastern", "label": "Eastern Time (EST/EDT)"},
        {"value": "US/Central", "label": "Central Time (CST/CDT)"},
        {"value": "US/Mountain", "label": "Mountain Time (MST/MDT)"},
        {"value": "US/Pacific", "label": "Pacific Time (PST/PDT)"},
        {"value": "UTC", "label": "UTC"},
        {"value": "Europe/London", "label": "London Time (GMT/BST)"},
        {"value": "Europe/Paris", "label": "Paris Time (CET/CEST)"},
        {"value": "Asia/Tokyo", "label": "Tokyo Time (JST)"},
        {"value": "Australia/Sydney", "label": "Sydney Time (AEST/AEDT)"},
    ]
    return common_timezones


