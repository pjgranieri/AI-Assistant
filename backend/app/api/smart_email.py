from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.deps import get_db
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter()

class SmartEmailRequest(BaseModel):
    subject: str
    content: str
    sender: str = ""

class SmartEmailResponse(BaseModel):
    traditional_analysis: Dict[str, Any]
    agent_analysis: Dict[str, Any]
    smart_suggestions: List[str]
    routing_confidence: float

@router.post("/smart-analysis", response_model=SmartEmailResponse)
def analyze_email_smart(request: SmartEmailRequest):
    """Analyze email with LangChain agent routing"""
    try:
        # Import here to avoid circular imports and startup issues
        from app.services.langchain_agent import SmartEmailProcessor
        
        processor = SmartEmailProcessor()
        
        email_data = {
            'subject': request.subject,
            'content': request.content,
            'sender': request.sender
        }
        
        result = processor.process_email_with_routing(email_data)
        
        return SmartEmailResponse(
            traditional_analysis={
                'summary': result.get('summary', ''),
                'sentiment': result.get('sentiment', ''),
                'priority': result.get('priority', ''),
                'category': result.get('category', ''),
                'action_items': result.get('action_items', '')
            },
            agent_analysis=result['agent_analysis'],
            smart_suggestions=result['smart_suggestions'],
            routing_confidence=result['routing_confidence']
        )
        
    except Exception as e:
        print(f"Smart analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Smart analysis failed: {str(e)}")

@router.post("/create-from-email")
def create_items_from_email(request: SmartEmailRequest, db: Session = Depends(get_db)):
    """Create calendar events and tasks from email analysis"""
    try:
        # Import here to avoid startup issues
        from app.services.langchain_agent import SmartEmailProcessor
        
        processor = SmartEmailProcessor()
        
        email_data = {
            'subject': request.subject,
            'content': request.content,
            'sender': request.sender
        }
        
        result = processor.process_email_with_routing(email_data)
        agent_analysis = result['agent_analysis']
        
        created_items = {
            'events': [],
            'tasks': []
        }
        
        # For now, just return the analysis without creating actual items
        # You can implement actual event/task creation later
        if agent_analysis.get('contains_event'):
            created_items['events'].append({
                'title': agent_analysis.get('event_details', {}).get('title', 'New Event'),
                'suggested': True
            })
            
        if agent_analysis.get('contains_tasks'):
            task_details = agent_analysis.get('task_details', {})
            if task_details.get('tasks'):
                created_items['tasks'] = task_details['tasks']
        
        return created_items
        
    except Exception as e:
        print(f"Item creation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Item creation failed: {str(e)}")