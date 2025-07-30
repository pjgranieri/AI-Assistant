from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models.event import Event
from app.deps import get_db
from pydantic import BaseModel
from typing import List, Optional
import datetime

router = APIRouter()

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    date: Optional[datetime.datetime] = None

class EventRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    date: datetime.datetime

    class Config:
        orm_mode = True

@router.post("/create", response_model=EventRead)
def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = Event(
        title=event.title,
        description=event.description,
        date=event.date or datetime.datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("/get", response_model=List[EventRead])
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).all()