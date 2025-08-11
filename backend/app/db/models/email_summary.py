from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import JSONB  # ensure available (Postgres)
from pgvector.sqlalchemy import Vector
from app.db.base import Base
import datetime as dt

class EmailSummary(Base):
    __tablename__ = "email_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Google user ID from auth
    gmail_id = Column(String, unique=True, index=True)  # Gmail message ID
    subject = Column(String, nullable=False)
    sender = Column(String)
    recipient = Column(String)
    content = Column(Text)  # Full email content
    summary = Column(Text, nullable=False)  # AI-generated summary
    embedding = Column(Vector(1536))  # OpenAI ada-002 embeddings are 1536 dimensions
    sentiment = Column(String)  # positive, negative, neutral
    priority = Column(String)  # high, medium, low
    category = Column(String)  # work, personal, promotional, etc.
    action_items = Column(Text)  # Extracted action items
    received_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, default=dt.datetime.utcnow)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    processing_status = Column(String, default="processed")  # processed, failed, pending
    processing_cost = Column(Float, default=0.0)  # Track LLM costs
    last_processed = Column(DateTime, default=dt.datetime.utcnow)

    # --- New agent-driven enrichment columns ---
    agent_analysis = Column(JSONB, nullable=True)          # full structured JSON
    primary_type = Column(String, nullable=True)
    urgency = Column(String, nullable=True)
    contains_event = Column(Boolean, default=False)
    contains_tasks = Column(Boolean, default=False)
    tool_chain_used = Column(Boolean, server_default="false", default=False)