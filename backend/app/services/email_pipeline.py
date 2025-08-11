from typing import Dict, Any
from sqlalchemy.orm import Session
from app.db.models.email_summary import EmailSummary
from app.services.langchain_agent import SmartEmailProcessor
from app.services.summarizer import ContentSummarizer
import datetime as dt

agent_processor = SmartEmailProcessor()
legacy_processor = ContentSummarizer()

def process_email_with_agent(
    user_id: str,
    gmail_id: str,
    subject: str,
    sender: str,
    recipient: str,
    content: str,
    received_at: dt.datetime
) -> EmailSummary:
    """Process email with agent and return EmailSummary object"""
    payload = {"subject": subject, "content": content, "sender": sender}
    
    try:
        print(f"[INFO] Processing with agent: {subject[:50]}...")
        result = agent_processor.process_email_with_routing(payload)
        analysis = result.get("agent_analysis", {})
        
        summary = analysis.get("summary") or analysis.get("reasoning") or ""
        
        return EmailSummary(
            user_id=user_id,
            gmail_id=gmail_id,
            subject=subject,
            sender=sender,
            recipient=recipient,
            content=content,
            summary=summary,
            sentiment=analysis.get("sentiment"),
            priority=analysis.get("priority") or "medium",
            category=analysis.get("primary_type") or "informational",
            action_items=_serialize_tasks(analysis.get("task_details")),
            received_at=received_at,
            processed_at=dt.datetime.utcnow(),
            # Agent-specific fields
            agent_analysis=analysis,
            primary_type=analysis.get("primary_type"),
            urgency=analysis.get("urgency"),
            contains_event=bool(analysis.get("contains_event")),
            contains_tasks=bool(analysis.get("contains_tasks")),
            tool_chain_used=bool(analysis.get("tool_chain_used"))
        )
        
    except Exception as e:
        print(f"[WARN] Agent failed for {subject[:30]}, using fallback: {e}")
        
        # Fallback to legacy processor
        legacy_summary = legacy_processor.summarize_email(content, subject)
        
        return EmailSummary(
            user_id=user_id,
            gmail_id=gmail_id,
            subject=subject,
            sender=sender,
            recipient=recipient,
            content=content,
            summary=legacy_summary,
            priority="medium",
            category="informational",
            received_at=received_at,
            processed_at=dt.datetime.utcnow(),
            tool_chain_used=False
        )

def _serialize_tasks(task_details):
    """Convert task details to string for action_items column"""
    if not task_details or not task_details.get("tasks"):
        return None
    tasks = task_details["tasks"]
    return "; ".join([task.get("description", "") for task in tasks if task.get("description")])