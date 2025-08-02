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
    datetime: Optional[dt.datetime] = None

class EventRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    datetime: dt.datetime

    model_config = {"from_attributes": True}

@router.post("/events", response_model=EventRead)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = Event(
        title=event.title,
        description=event.description,
        datetime=event.datetime or dt.datetime.utcnow()
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
    db_event.datetime = event.datetime or db_event.datetime
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


