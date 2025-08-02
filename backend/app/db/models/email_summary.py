from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.base import Base
import datetime

class EmailSummary(Base):
    __tablename__ = "email_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    received_at = Column(DateTime, default=datetime.datetime.utcnow)