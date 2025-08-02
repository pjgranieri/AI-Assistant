from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base
import datetime

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    # Add embedding if needed