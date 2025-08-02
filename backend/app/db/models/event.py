from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base
import datetime as dt

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    datetime = Column(DateTime, default=dt.datetime.utcnow)