import os
import datetime as dt
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re
from pydantic import BaseModel, ValidationError
from dateutil import parser as date_parser
import datetime

# Pydantic model for schema validation
class EventDetails(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = []
    duration_minutes: Optional[int] = None
    agenda: Optional[str] = None

class TaskDetails(BaseModel):
    tasks: List[Dict[str, Any]] = []
    
    class Config:
        # Allow extra fields in task objects
        extra = "allow"

class EmailAnalysis(BaseModel):
    primary_type: str
    contains_event: bool
    contains_tasks: bool
    urgency: str
    priority: str
    event_details: Optional[EventDetails] = None
    task_details: Optional[TaskDetails] = None
    recommendations: List[str]
    confidence: float
    reasoning: str

def aggregate_from_steps(steps: List[tuple]) -> Dict[str, Any]:
    """
    Aggregate analysis from intermediate tool steps when JSON parsing fails.
    steps is a list of tuples: (AgentAction, tool_output)
    """
    print(f"🔧 Aggregating from {len(steps)} tool steps...")
    
    out = {
        "primary_type": "informational",
        "contains_event": False,
        "contains_tasks": False,
        "urgency": "low",
        "priority": "low",
        "event_details": None,
        "task_details": {"tasks": []},
        "recommendations": [],
        "confidence": 0.5,
        "reasoning": "Aggregated from tool steps."
    }
    
    confidences = []
    reasoning_parts = []
    tools_executed = set()
    
    for call, output in steps:
        name = getattr(call, "tool", None)
        tools_executed.add(name)
        print(f"  Processing tool: {name}")
        
        try:
            payload = json.loads(output) if isinstance(output, str) else output
        except Exception as e:
            print(f"    ❌ Failed to parse tool output: {e}")
            continue
        
        print(f"    ✅ Parsed payload: {list(payload.keys()) if isinstance(payload, dict) else type(payload)}")
        
        if name == "classify_email_type":
            out["primary_type"] = payload.get("type") or out["primary_type"]
            conf = payload.get("confidence", 0.5)
            confidences.append(conf)
            reasoning_parts.append(f"Classified as {out['primary_type']} ({conf:.2f})")
            
        elif name == "detect_event":
            if payload.get("contains_event"):
                out["contains_event"] = True
                conf = payload.get("confidence", 0.8)
                confidences.append(conf)
                reasoning_parts.append(f"Event detected ({conf:.2f})")
            else:
                # Still record confidence even if no event found
                conf = payload.get("confidence", 0.7)
                confidences.append(conf)
                reasoning_parts.append(f"No event detected ({conf:.2f})")
                
        elif name == "extract_event_details" and out["contains_event"]:
            # Ensure event_details are properly extracted and populated
            event_details = payload if isinstance(payload, dict) else {}
            if event_details:
                # Clean up and ensure we have meaningful data
                cleaned_details = {}
                for key, value in event_details.items():
                    if value is not None and value != "" and value != []:
                        cleaned_details[key] = value
                
                # SCHEMA VALIDATION FIXES for aggregated event details
                if cleaned_details:
                    # Fix attendees - must always be a list of strings
                    if 'attendees' in cleaned_details:
                        attendees = cleaned_details['attendees']
                        if isinstance(attendees, str):
                            # Single string - check if comma-separated
                            if ',' in attendees:
                                cleaned_details['attendees'] = [name.strip() for name in attendees.split(',') if name.strip()]
                            else:
                                cleaned_details['attendees'] = [attendees] if attendees.strip() else []
                        elif isinstance(attendees, list):
                            # Clean up list items
                            cleaned_attendees = []
                            for attendee in attendees:
                                if isinstance(attendee, str) and attendee.strip():
                                    cleaned_attendees.append(attendee.strip())
                                elif attendee:
                                    cleaned_attendees.append(str(attendee).strip())
                            cleaned_details['attendees'] = cleaned_attendees
            
                    # Fix agenda - must always be a single string
                    if 'agenda' in cleaned_details:
                        agenda = cleaned_details['agenda']
                        if isinstance(agenda, list):
                            cleaned_details['agenda'] = '; '.join(str(item) for item in agenda if item)
                        elif agenda is not None:
                            cleaned_details['agenda'] = str(agenda)
            
                    # Ensure duration_minutes is int or None
                    if 'duration_minutes' in cleaned_details and cleaned_details['duration_minutes'] is not None:
                        try:
                            cleaned_details['duration_minutes'] = int(cleaned_details['duration_minutes'])
                        except (ValueError, TypeError):
                            cleaned_details['duration_minutes'] = None
            
            out["event_details"] = cleaned_details
            reasoning_parts.append("Event details extracted")
            
        elif name == "detect_tasks":
            if payload.get("contains_tasks"):
                out["contains_tasks"] = True
                conf = payload.get("confidence", 0.8)
                confidences.append(conf)
                reasoning_parts.append(f"Tasks detected ({conf:.2f})")
            else:
                # Still record confidence even if no tasks found
                conf = payload.get("confidence", 0.7)
                confidences.append(conf)
                reasoning_parts.append(f"No tasks detected ({conf:.2f})")
                
        elif name == "extract_task_details" and out["contains_tasks"]:
            # Ensure task_details are properly extracted and populated
            task_details = payload if isinstance(payload, dict) else {}
            if task_details and task_details.get("tasks"):
                # Clean up task data
                cleaned_tasks = []
                for task in task_details.get("tasks", []):
                    if isinstance(task, dict) and task.get("description"):  # Changed from 'title' to 'description'
                        cleaned_tasks.append(task)
                
                if cleaned_tasks:  # Only set if we have actual tasks
                    out["task_details"] = {"tasks": cleaned_tasks}
                    reasoning_parts.append("Task details extracted")
            
        elif name == "analyze_urgency":
            out["urgency"] = payload.get("urgency", out["urgency"])
            out["priority"] = payload.get("priority", out["priority"])
            conf = payload.get("confidence", 0.8)
            confidences.append(conf)
            reasoning_parts.append(f"Urgency: {out['urgency']}, Priority: {out['priority']} ({conf:.2f})")
    
    # PRIMARY TYPE LOGIC - Set to "mixed" if both event and tasks are found
    if out["contains_event"] and out["contains_tasks"]:
        out["primary_type"] = "mixed"
        reasoning_parts.append("Mixed content: both event and tasks detected")
    
    # ALWAYS INCLUDE ALL RECOMMENDATIONS for mixed cases
    recommendations = []
    
    # Priority order: mark_priority first if urgency is medium or high
    if out["urgency"] in ["medium", "high", "critical"]:
        recommendations.append("mark_priority")
    
    # Then calendar and task actions - BOTH if detected (even if mixed)
    if out["contains_event"]:
        recommendations.append("create_calendar_event")
    if out["contains_tasks"]:
        recommendations.append("add_to_task_list")
    
    # Add default if no specific recommendations
    if not recommendations:
        recommendations.append("no_action")
    
    # Deduplicate while preserving order
    out["recommendations"] = list(dict.fromkeys(recommendations))
    
    # CONFIDENCE: Use minimum of key detection confidences (not max) for more conservative estimate
    key_confidences = []
    if "detect_event" in tools_executed:
        # Find the detect_event confidence
        for call, output in steps:
            if getattr(call, "tool", None) == "detect_event":
                try:
                    payload = json.loads(output) if isinstance(output, str) else output
                    key_confidences.append(payload.get("confidence", 0.5))
                except:
                    key_confidences.append(0.5)
                break
    
    if "detect_tasks" in tools_executed:
        # Find the detect_tasks confidence
        for call, output in steps:
            if getattr(call, "tool", None) == "detect_tasks":
                try:
                    payload = json.loads(output) if isinstance(output, str) else output
                    key_confidences.append(payload.get("confidence", 0.5))
                except:
                    key_confidences.append(0.5)
                break
    
    # Use minimum of key confidences, or average of all if no key ones found
    if key_confidences:
        out["confidence"] = min(key_confidences)
    else:
        out["confidence"] = sum(confidences) / len(confidences) if confidences else 0.5
    
    # FULL REASONING WITHOUT TRUNCATION
    out["reasoning"] = "; ".join(reasoning_parts) if reasoning_parts else "Aggregated from tool steps"
    
    print(f"📊 Aggregated result: {out['primary_type']}, event={out['contains_event']}, tasks={out['contains_tasks']}")
    print(f"💡 Recommendations: {out['recommendations']}")
    print(f"🎯 Final confidence: {out['confidence']:.2f}")
    
    # Apply normalization to aggregated results too
    # Note: We don't have the original email text here, so pass empty string
    out = normalize_final_analysis(out, "")
    
    return out

def normalize_final_analysis(final_analysis: Dict[str, Any], original_email_text: str = "") -> Dict[str, Any]:
    """
    Post-processing layer to normalize final analysis before validation.
    Handles event details completeness, reasoning de-duplication, and date normalization.
    """
    print("🔧 Normalizing final analysis...")
    
    # Create a copy to avoid modifying the original
    normalized = final_analysis.copy()
    
    # === EVENT DETAILS COMPLETENESS ===
    if normalized.get('event_details') and isinstance(normalized['event_details'], dict):
        event_details = normalized['event_details'].copy()
        
        # Fix attendees - ensure it's a list[str]
        if 'attendees' in event_details:
            attendees = event_details['attendees']
            if isinstance(attendees, str):
                # Single string - check if comma/semicolon separated
                if any(sep in attendees for sep in [',', ';', ' and ']):
                    # Split by multiple separators and clean up
                    import re
                    names = re.split(r'[,;]|\s+and\s+', attendees)
                    event_details['attendees'] = [name.strip() for name in names if name.strip()]
                else:
                    # Single attendee
                    event_details['attendees'] = [attendees.strip()] if attendees.strip() else []
            elif not isinstance(attendees, list):
                event_details['attendees'] = []
        
        # Light inference for missing attendees
        if not event_details.get('attendees') and original_email_text:
            # Look for "Attendees:" section in email
            lines = original_email_text.split('\n')
            for i, line in enumerate(lines):
                if 'attendees:' in line.lower() or 'attendees -' in line.lower():
                    # Get the content after "Attendees:"
                    attendee_text = line.split(':', 1)[-1].strip()
                    if not attendee_text and i + 1 < len(lines):
                        # Check next line if current line only has "Attendees:"
                        attendee_text = lines[i + 1].strip()
                    
                    if attendee_text:
                        # Split by common separators
                        import re
                        names = re.split(r'[,;]|\s+and\s+', attendee_text)
                        cleaned_names = [name.strip() for name in names if name.strip()]
                        if cleaned_names:
                            event_details['attendees'] = cleaned_names
                            print(f"  ✅ Inferred attendees: {cleaned_names}")
                            break
        
        # Fix agenda - ensure it's a string
        if 'agenda' in event_details:
            agenda = event_details['agenda']
            if isinstance(agenda, list):
                # Join list items with semicolon
                event_details['agenda'] = '; '.join(str(item).strip() for item in agenda if str(item).strip())
            elif agenda is None:
                event_details['agenda'] = None
            else:
                event_details['agenda'] = str(agenda).strip() if agenda else None
        
        # Light inference for missing agenda
        if not event_details.get('agenda') and original_email_text:
            # Look for agenda-related sections
            lines = original_email_text.split('\n')
            agenda_items = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                # Check for agenda keywords
                if any(keyword in line_lower for keyword in ['agenda:', 'agenda -', 'before the meeting', 'action items:', 'we need to']):
                    # Get content after the keyword
                    if ':' in line:
                        content = line.split(':', 1)[-1].strip()
                        if content:
                            agenda_items.append(content)
                    
                    # Check next few lines for bullet points or list items
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and (next_line.startswith('-') or next_line.startswith('•') or next_line.startswith('*')):
                            # Remove bullet point and add to agenda
                            item = next_line[1:].strip()
                            if item and len(item) < 100:  # Keep it conservative
                                agenda_items.append(item)
                        elif next_line and not next_line.startswith(' ') and len(agenda_items) > 0:
                            # Stop if we hit a non-indented line
                            break
            
            if agenda_items:
                # Keep only first 2-4 items and join
                agenda_text = '; '.join(agenda_items[:4])
                if len(agenda_text) < 200:  # Keep it conservative
                    event_details['agenda'] = agenda_text
                    print(f"  ✅ Inferred agenda: {agenda_text}")
        
        # === DATE NORMALIZATION ===
        if event_details.get('datetime'):
            original_datetime = event_details['datetime']
            try:
                # Use dateutil to parse flexible date formats
                reference_dt = datetime.datetime.now()
                parsed_dt = date_parser.parse(original_datetime, fuzzy=True, default=reference_dt)
                
                # Only update if we got a reasonable parse (not just default time)
                if parsed_dt != reference_dt.replace(hour=0, minute=0, second=0, microsecond=0):
                    event_details['datetime'] = parsed_dt.strftime('%Y-%m-%dT%H:%M:%S')
                    print(f"  ✅ Normalized datetime: {original_datetime} → {event_details['datetime']}")
            except Exception as e:
                print(f"  ⚠️ Date parsing failed for '{original_datetime}': {e}")
                # Keep original value
                pass
        
        normalized['event_details'] = event_details
    
    # === REASONING DE-DUPLICATION ===
    if normalized.get('reasoning'):
        reasoning = normalized['reasoning']
        
        # Split into sentences
        sentences = [s.strip() for s in reasoning.split('.') if s.strip()]
        
        # Remove duplicate sentences while preserving order
        seen_sentences = set()
        deduped_sentences = []
        
        for sentence in sentences:
            # Normalize for comparison (lowercase, remove extra spaces)
            normalized_sentence = ' '.join(sentence.lower().split())
            
            if normalized_sentence not in seen_sentences:
                seen_sentences.add(normalized_sentence)
                deduped_sentences.append(sentence)
        
        # Handle repeated clauses within sentences
        final_sentences = []
        for sentence in deduped_sentences:
            # Check for repeated phrases like "The email explicitly states" back-to-back
            words = sentence.split()
            if len(words) > 6:
                # Look for repeated 3-4 word phrases
                for phrase_len in [4, 3]:
                    for i in range(len(words) - phrase_len * 2 + 1):
                        phrase1 = ' '.join(words[i:i + phrase_len])
                        phrase2 = ' '.join(words[i + phrase_len:i + phrase_len * 2])
                        if phrase1.lower() == phrase2.lower():
                            # Remove the duplicate phrase
                            words = words[:i + phrase_len] + words[i + phrase_len * 2:]
                            break
            
            final_sentences.append(' '.join(words))
        
        # Rejoin with single space between sentences
        deduplicated_reasoning = '. '.join(final_sentences)
        if deduplicated_reasoning and not deduplicated_reasoning.endswith('.'):
            deduplicated_reasoning += '.'
        
        normalized['reasoning'] = deduplicated_reasoning
        
        if deduplicated_reasoning != reasoning:
            print(f"  ✅ De-duplicated reasoning: {len(reasoning)} → {len(deduplicated_reasoning)} chars")
    
    print("✅ Final analysis normalization complete")
    return normalized

class EmailRouterAgent:
    """LangChain agent for intelligent email routing and processing"""
    
    def __init__(self):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Verify API key is available
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY not found in environment variables")
    
        # Set temperature to 0 for deterministic results
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        self.tools = self._create_tools()
        self.agent = self._create_agent()
    
    def _create_tools(self) -> List[Tool]:
        """Create specialized tools for email analysis"""
        
        def classify_email_type_tool(email_content: str) -> str:
            """Tool to classify the primary type of email"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Classify this email into ONE primary category:
                - event: Meeting invitations, appointments, calendar items
                - task: Action items, requests, deadlines, assignments
                - informational: News, updates, announcements, FYI
                - promotional: Marketing, sales, advertisements
                - automated: System notifications, receipts, confirmations
                - personal: Personal communications, casual messages
                - urgent: Time-sensitive items requiring immediate attention
                
                Return only valid JSON: {{"type": "category", "confidence": 0.0-1.0, "reasoning": "explanation"}}"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            # Ensure we return valid JSON
            try:
                json.loads(result)
                return result
            except:
                return json.dumps({"type": "informational", "confidence": 0.5, "reasoning": "Classification failed"})
        
        def detect_event_tool(email_content: str) -> str:
            """Tool to detect if email contains event information"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Analyze if this email contains event information.
                Look for:
                - Meeting invitations or scheduling
                - Appointments (medical, business, personal)
                - Conferences, webinars, workshops
                - Social events, parties, gatherings
                - Travel bookings or itineraries
                - Deadlines with specific dates/times
                
                Return only valid JSON: {{"contains_event": true/false, "confidence": 0.0-1.0, "event_type": "meeting|appointment|conference|social|travel|deadline", "reasoning": "explanation"}}"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            try:
                json.loads(result)
                return result
            except:
                return json.dumps({"contains_event": False, "confidence": 0.5, "event_type": None, "reasoning": "Event detection failed"})
        
        def extract_event_details_tool(email_content: str) -> str:
            """Tool to extract specific event details"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract event details from this email.
                Look for:
                - Title/subject of the event
                - Date and time (be specific about format)
                - Location (physical or virtual)
                - Attendees or participants
                - Duration or end time
                - Important notes or agenda items
                
                Return only valid JSON with these fields:
                title, description, datetime, end_datetime, location, attendees, duration_minutes, agenda"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            try:
                parsed = json.loads(result)
                
                # SCHEMA VALIDATION FIXES - Ensure proper data types
                if isinstance(parsed, dict):
                    # Fix attendees - must always be a list of strings
                    if 'attendees' in parsed:
                        attendees = parsed['attendees']
                        if isinstance(attendees, str):
                            # Single string - check if comma-separated
                            if ',' in attendees:
                                # Split and clean up
                                parsed['attendees'] = [name.strip() for name in attendees.split(',') if name.strip()]
                            else:
                                # Single attendee - wrap in list
                                parsed['attendees'] = [attendees] if attendees.strip() else []
                        elif isinstance(attendees, list):
                            # Already a list - ensure all items are strings and clean up
                            cleaned_attendees = []
                            for attendee in attendees:
                                if isinstance(attendee, str) and attendee.strip():
                                    cleaned_attendees.append(attendee.strip())
                                elif attendee:  # Non-string but truthy
                                    cleaned_attendees.append(str(attendee).strip())
                            parsed['attendees'] = cleaned_attendees
                        else:
                            # Other type - convert to empty list
                            parsed['attendees'] = []
                    else:
                        # Missing attendees field - add empty list
                        parsed['attendees'] = []
                    
                    # Fix agenda - must always be a single string
                    if 'agenda' in parsed:
                        agenda = parsed['agenda']
                        if isinstance(agenda, list):
                            # List - join into single string
                            parsed['agenda'] = '; '.join(str(item) for item in agenda if item)
                        elif agenda is None:
                            parsed['agenda'] = None
                        else:
                            # Convert to string if not already
                            parsed['agenda'] = str(agenda) if agenda else None
                    
                    # Ensure duration_minutes is int or None
                    if 'duration_minutes' in parsed and parsed['duration_minutes'] is not None:
                        try:
                            parsed['duration_minutes'] = int(parsed['duration_minutes'])
                        except (ValueError, TypeError):
                            parsed['duration_minutes'] = None
                
                return json.dumps(parsed)
                
            except json.JSONDecodeError:
                # Fallback for invalid JSON
                return json.dumps({
                    "title": None, 
                    "description": None, 
                    "datetime": None, 
                    "end_datetime": None, 
                    "location": None, 
                    "attendees": [], 
                    "duration_minutes": None, 
                    "agenda": None
                })
            except Exception as e:
                print(f"Error processing event details: {e}")
                return json.dumps({
                    "title": None, 
                    "description": None, 
                    "datetime": None, 
                    "end_datetime": None, 
                    "location": None, 
                    "attendees": [], 
                    "duration_minutes": None, 
                    "agenda": None
                })
        
        def detect_tasks_tool(email_content: str) -> str:
            """Tool to detect actionable tasks"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Analyze if this email contains actionable tasks.
                Look for:
                - Explicit requests or assignments
                - Action items to complete
                - Follow-up actions needed
                - Deadlines or due dates
                - Required responses or deliverables
                
                Return only valid JSON: {{"contains_tasks": true/false, "confidence": 0.0-1.0, "task_count": number, "urgency": "low|medium|high", "reasoning": "explanation"}}"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            try:
                json.loads(result)
                return result
            except:
                return json.dumps({"contains_tasks": False, "confidence": 0.5, "task_count": 0, "urgency": "low", "reasoning": "Task detection failed"})
        
        def extract_task_details_tool(email_content: str) -> str:
            """Tool to extract specific task details"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract actionable tasks from this email.
                Look for explicit requests, action items, or things that need to be done.
                
                Return only valid JSON with a tasks array where each task is an object with these fields:
                - description: (required) What needs to be done
                - due_date: Date/deadline if mentioned (or null)
                - priority: "low|medium|high" based on context (or null)
                - assignee: Who should do it if specified (or null)
                - category: Type of task if clear (or null)
                
                Example format:
                {{
                    "tasks": [
                        {{
                            "description": "Complete the requirements document",
                            "due_date": "before the meeting",
                            "priority": "medium",
                            "assignee": null,
                            "category": "documentation"
                        }},
                        {{
                            "description": "Prepare a 5-minute presentation",
                            "due_date": "before the meeting", 
                            "priority": "medium",
                            "assignee": null,
                            "category": "presentation"
                        }}
                    ]
                }}
                
                If no tasks are found, return: {{"tasks": []}}"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            try:
                parsed = json.loads(result)
                # Ensure each task has at least a description field
                if isinstance(parsed, dict) and 'tasks' in parsed:
                    cleaned_tasks = []
                    for task in parsed['tasks']:
                        if isinstance(task, dict):
                            # Ensure description field exists
                            if 'description' not in task or not task['description']:
                                continue  # Skip invalid tasks
                            cleaned_tasks.append(task)
                        elif isinstance(task, str):
                            # Convert string to proper task object
                            cleaned_tasks.append({"description": task, "due_date": None, "priority": None, "assignee": None, "category": None})
                
                return json.dumps({"tasks": cleaned_tasks})
            except:
                return json.dumps({"tasks": []})
        
        def analyze_urgency_tool(email_content: str) -> str:
            """Tool to analyze urgency and priority"""
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Analyze the urgency and priority of this email.
                Consider:
                - Explicit urgency indicators (URGENT, ASAP, etc.)
                - Deadlines and time sensitivity
                - Sender importance
                - Subject matter criticality
                
                Return only valid JSON: {{"urgency": "low|medium|high|critical", "priority": "low|medium|high", "time_sensitive": true/false, "reasoning": "explanation"}}"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            try:
                json.loads(result)
                return result
            except:
                return json.dumps({"urgency": "medium", "priority": "medium", "time_sensitive": False, "reasoning": "Urgency analysis failed"})

        return [
            Tool(
                name="classify_email_type",
                description="Classify the primary type of email (event, task, informational, etc.)",
                func=classify_email_type_tool
            ),
            Tool(
                name="detect_event",
                description="Detect if email contains event information like meetings or appointments",
                func=detect_event_tool
            ),
            Tool(
                name="extract_event_details",
                description="Extract specific event details like date, time, location from email",
                func=extract_event_details_tool
            ),
            Tool(
                name="detect_tasks",
                description="Detect if email contains actionable tasks or assignments",
                func=detect_tasks_tool
            ),
            Tool(
                name="extract_task_details",
                description="Extract specific task details like deadlines and priorities",
                func=extract_task_details_tool
            ),
            Tool(
                name="analyze_urgency",
                description="Analyze the urgency and priority level of the email",
                func=analyze_urgency_tool
            )
        ]
    
    def _create_agent(self) -> AgentExecutor:
        """Create the main routing agent with tool chaining"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent email routing agent that uses specialized tools to analyze emails comprehensively.

CRITICAL WORKFLOW - Execute ALL these steps for EVERY email:
1. ALWAYS classify the email type using classify_email_type
2. ALWAYS check for events using detect_event (regardless of initial classification)
3. IF detect_event finds an event, ALWAYS use extract_event_details
4. ALWAYS check for tasks using detect_tasks (regardless of initial classification)  
5. IF detect_tasks finds tasks, ALWAYS use extract_task_details
6. ALWAYS analyze urgency using analyze_urgency

IMPORTANT: Even if the email seems primarily about events, it may ALSO contain tasks. 
Even if it seems primarily about tasks, it may ALSO contain events.
ALWAYS check both possibilities - never skip detect_event or detect_tasks.

RECOMMENDATIONS LOGIC:
- If urgency is medium/high/critical: include "mark_priority"
- If contains_event is true: include "create_calendar_event" 
- If contains_tasks is true: include "add_to_task_list"
- Include ALL applicable recommendations, even if both events and tasks are present

After using ALL necessary tools, output **only** one JSON object with these exact keys:
{{
    "primary_type": "event|task|informational|promotional|automated|personal|urgent|mixed",
    "contains_event": true/false,
    "contains_tasks": true/false,
    "urgency": "low|medium|high|critical",
    "priority": "low|medium|high",
    "event_details": {{...}} or null,
    "task_details": {{"tasks": [{{...}}]}} or null,
    "recommendations": ["create_calendar_event", "add_to_task_list", "mark_priority", "no_action"],
    "confidence": 0.0-1.0,
    "reasoning": "step-by-step analysis explanation"
}}

Set primary_type to "mixed" if BOTH contains_event AND contains_tasks are true.
Include ALL relevant recommendations based on what you found.
Ensure task_details.tasks contains objects with description field, not strings.
Do not include any prose outside the JSON. Only return the JSON object."""),
            ("human", "Analyze this email comprehensively:\n\n{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        
        # CRITICAL: Ensure we return intermediate steps and keep deterministic
        return AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            return_intermediate_steps=True,  # MUST be True
            handle_parsing_errors=True,
            verbose=True,
            max_iterations=8  # Increased to allow for all 6 tools + some reasoning
        )
    
    def analyze_email(self, subject: str, content: str, sender: str = "") -> Dict[str, Any]:
        """Main method to analyze an email with tool chaining"""
        try:
            # Truncate content if too long
            max_content_length = 6000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "... [Content truncated]"
            
            # Combine subject and content for analysis
            email_text = f"Subject: {subject}\n\nContent: {content}"
            
            # Run the agent with tool chaining
            res = self.agent.invoke({"input": email_text})
            
            # Extract intermediate steps and check if tool chain was used
            steps = res.get("intermediate_steps", [])
            tool_chain_used = bool(steps)
            
            print(f"\n🔧 Debug: Found {len(steps)} intermediate steps")
            print(f"🔗 Tool Chain Used: {tool_chain_used}")
            
            # Log tools that were executed
            tools_executed = []
            for step in steps:
                if len(step) >= 2:
                    action = step[0]
                    tool_name = getattr(action, 'tool', 'unknown')
                    tools_executed.append(tool_name)
                    print(f"  🔧 Executed: {tool_name}")
            
            # Try to parse the agent's final JSON output
            raw_output = res.get("output", "")
            print(f"📄 Raw agent output: {raw_output[:200]}...")
            
            try:
                # Try to extract JSON from the output
                json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    final_analysis = json.loads(json_str)
                    print("✅ Successfully parsed agent's JSON output")
                    
                    # Apply PRIMARY TYPE LOGIC for agent output too
                    if final_analysis.get("contains_event") and final_analysis.get("contains_tasks"):
                        final_analysis["primary_type"] = "mixed"
                    
                    # === POST-PROCESSING NORMALIZATION ===
                    final_analysis = normalize_final_analysis(final_analysis, email_text)
                    
                    # Validate with Pydantic model
                    try:
                        validated = EmailAnalysis(**final_analysis)
                        final_analysis = validated.dict()
                        print("✅ Schema validation passed")
                    except ValidationError as e:
                        print(f"⚠️ Schema validation failed: {e}")
                        # Use the JSON anyway if it has required keys
                        required_keys = ["primary_type", "contains_event", "contains_tasks", "urgency", "priority"]
                        if all(key in final_analysis for key in required_keys):
                            print("✅ Using JSON despite validation issues")
                        else:
                            raise ValueError("Missing required keys")
                else:
                    raise ValueError("No JSON found in agent output")
                    
            except Exception as e:
                print(f"❌ JSON parsing failed: {e}")
                print("🔄 Falling back to aggregating from tool steps")
                final_analysis = aggregate_from_steps(steps)
                
                # === POST-PROCESSING NORMALIZATION FOR FALLBACK ===
                final_analysis = normalize_final_analysis(final_analysis, email_text)
        
            # ALWAYS INCLUDE ALL RECOMMENDATIONS - Apply to all paths
            recommendations = []
            
            # Priority order: mark_priority first if urgency is medium or high
            urgency = final_analysis.get("urgency", "low")
            if urgency in ["medium", "high", "critical"]:
                recommendations.append("mark_priority")
            
            # Then calendar and task actions - INCLUDE BOTH if both are detected
            if final_analysis.get("contains_event"):
                recommendations.append("create_calendar_event")
            if final_analysis.get("contains_tasks"):
                recommendations.append("add_to_task_list")
            
            # Add default if no specific recommendations
            if not recommendations:
                recommendations.append("no_action")
            
            # Deduplicate while preserving order
            final_analysis["recommendations"] = list(dict.fromkeys(recommendations))
            
            # CONFIDENCE: Ensure it reflects actual tool performance, not defaults
            if tool_chain_used and steps:
                # Calculate confidence based on actual tool outputs
                tool_confidences = []
                for step in steps:
                    if len(step) >= 2:
                        try:
                            action, output = step
                            tool_name = getattr(action, 'tool', 'unknown')
                            if tool_name in ['detect_event', 'detect_tasks', 'analyze_urgency']:
                                payload = json.loads(output) if isinstance(output, str) else output
                                if isinstance(payload, dict) and 'confidence' in payload:
                                    tool_confidences.append(payload['confidence'])
                        except:
                            continue
                
                if tool_confidences:
                    # Use average of tool confidences, but cap it to be conservative
                    avg_confidence = sum(tool_confidences) / len(tool_confidences)
                    final_analysis["confidence"] = min(avg_confidence, 0.9)  # Cap at 0.9
            
            # PRIMARY TYPE LOGIC - Apply to agent output too
            if final_analysis.get("contains_event") and final_analysis.get("contains_tasks"):
                final_analysis["primary_type"] = "mixed"
            
            # Add metadata
            final_analysis['sender'] = sender
            final_analysis['processed_at'] = dt.datetime.utcnow().isoformat()
            final_analysis['tool_chain_used'] = tool_chain_used
            final_analysis['tools_executed'] = tools_executed
            
            return final_analysis
            
        except Exception as e:  # <-- Main exception handler, properly aligned
            # Handle any other errors
            return self._create_fallback_analysis(subject, content, str(e))
    
    def _create_fallback_analysis(self, subject: str, content: str, error: str = None) -> Dict[str, Any]:
        """Create a basic analysis if the agent fails"""
        
        # Use better simple classification
        contains_event = self._detect_event_simple(subject, content)
        contains_tasks = self._detect_task_simple(subject, content)
        
        # PRIMARY TYPE LOGIC for fallback
        if contains_event and contains_tasks:
            primary_type = "mixed"
        elif contains_event:
            primary_type = "event"
        elif contains_tasks:
            primary_type = "task"
        else:
            primary_type = self._classify_email_simple(subject, content)
        
        # Better urgency detection for fallback
        text = (subject + " " + content).lower()
        if any(word in text for word in ['urgent', 'asap', 'critical', 'immediate']):
            urgency = 'high'
            priority = 'high'
        elif any(word in text for word in ['deadline', 'due', 'tomorrow']):
            urgency = 'medium'
            priority = 'medium'
        else:
            urgency = 'low'
            priority = 'low'
        
        # ALWAYS INCLUDE ALL RECOMMENDATIONS for fallback
        recommendations = []
        
        # Priority order: mark_priority first if urgency is medium or high
        if urgency in ['medium', 'high', 'critical']:
            recommendations.append("mark_priority")
        
        # Then calendar and task actions - BOTH for any content that has both
        if contains_event:
            recommendations.append("create_calendar_event")
        if contains_tasks:
            recommendations.append("add_to_task_list")
        
        # Add default if no specific recommendations
        if not recommendations:
            recommendations.append("no_action")
        
        # FULL REASONING WITHOUT TRUNCATION for fallback
        reasoning_parts = [f"Fallback analysis used - {primary_type} type detected"]
        if error:
            reasoning_parts.append(f"Error: {error}")
        if contains_event:
            reasoning_parts.append("Event detected via simple classification")
        if contains_tasks:
            reasoning_parts.append("Tasks detected via simple classification")
        if contains_event and contains_tasks:
            reasoning_parts.append("Mixed content identified: both events and tasks present")
        
        reasoning = "; ".join(reasoning_parts)
        
        # Conservative confidence for fallback
        base_confidence = 0.6
        if contains_event and contains_tasks:
            base_confidence = 0.5  # Lower confidence for complex mixed content
        
        return {
            "primary_type": primary_type,
            "contains_event": contains_event,
            "contains_tasks": contains_tasks,
            "urgency": urgency,
            "priority": priority,
            "event_details": None,
            "task_details": {"tasks": []} if contains_tasks else None,
            "recommendations": recommendations,
            "confidence": base_confidence,
            "reasoning": reasoning,
            "sender": "",
            "processed_at": dt.datetime.utcnow().isoformat(),
            "tool_chain_used": False,
            "tools_executed": []
        }
    
    # Keep your existing simple classification methods as fallback
    def _classify_email_simple(self, subject: str, content: str) -> str:
        """Simple classification logic"""
        text = (subject + " " + content).lower()
        
        if any(word in text for word in ['meeting', 'appointment', 'calendar', 'schedule', 'conference']):
            return "event"
        elif any(word in text for word in ['task', 'action', 'complete', 'deadline', 'due', 'required']):
            return "task"
        elif any(word in text for word in ['urgent', 'asap', 'immediately', 'priority']):
            return "urgent"
        elif any(word in text for word in ['newsletter', 'update', 'news', 'announcement']):
            return "informational"
        elif any(word in text for word in ['sale', 'discount', 'offer', 'promotion']):
            return "promotional"
        else:
            return "personal"
    
    def _detect_event_simple(self, subject: str, content: str) -> bool:
        """Simple event detection"""
        text = (subject + " " + content).lower()
        event_keywords = ['meeting', 'appointment', 'conference', 'webinar', 'event', 'schedule', 'calendar']
        return any(word in text for word in event_keywords)
    
    def _detect_task_simple(self, subject: str, content: str) -> bool:
        """Simple task detection"""
        text = (subject + " " + content).lower()
        task_keywords = ['action required', 'please', 'complete', 'deadline', 'due', 'task', 'todo', 'follow up']
        return any(word in text for word in task_keywords)

# Keep your existing SmartEmailProcessor class
class SmartEmailProcessor:
    """Enhanced email processor with agent routing"""
    
    def __init__(self):
        # Import here to avoid circular imports
        try:
            from app.services.email_processor import EmailProcessor
            self.base_processor = EmailProcessor()
        except ImportError:
            print("Warning: EmailProcessor not available, using mock")
            self.base_processor = None
        
        self.agent = EmailRouterAgent()
    
    def process_email_with_routing(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email with both traditional analysis and agent routing"""
        
        # Get traditional analysis first (if available)
        if self.base_processor:
            try:
                traditional_analysis = self.base_processor.process_email(email_data)
            except Exception as e:
                print(f"Traditional analysis failed: {e}")
                traditional_analysis = {
                    'summary': email_data.get('content', '')[:200] + "...",
                    'sentiment': 'neutral',
                    'priority': 'medium',
                    'category': 'other',
                    'action_items': 'None',
                    'embedding': []
                }
        else:
            # Mock traditional analysis for testing
            traditional_analysis = {
                'summary': email_data.get('content', '')[:200] + "...",
                'sentiment': 'neutral',
                'priority': 'medium',
                'category': 'other',
                'action_items': 'None',
                'embedding': []
            }
        
        # Get agent analysis with tool chaining
        agent_analysis = self.agent.analyze_email(
            subject=email_data.get('subject', ''),
            content=email_data.get('content', ''),
            sender=email_data.get('sender', '')
        )
        
        # Combine both analyses
        combined_analysis = {
            **traditional_analysis,  # Keep original fields
            'agent_analysis': agent_analysis,
            'smart_suggestions': self._generate_smart_suggestions(agent_analysis),
            'routing_confidence': agent_analysis.get('confidence', 0.0)
        }
        
        return combined_analysis
    
    def _generate_smart_suggestions(self, agent_analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable suggestions based on agent analysis"""
        suggestions = []
        
        print(f"🎯 Generating suggestions from: {agent_analysis}")
        
        # Check for events
        if agent_analysis.get('contains_event'):
            suggestions.append("📅 Create calendar event")
            
            # Add specific event suggestions
            event_details = agent_analysis.get('event_details')
            if event_details:
                if event_details.get('datetime'):
                    suggestions.append("⏰ Set reminder")
                if event_details.get('attendees'):
                    suggestions.append("👥 Invite attendees")
        
        # Check for tasks
        if agent_analysis.get('contains_tasks'):
            suggestions.append("✅ Add to task list")
            
            # Add specific task suggestions
            task_details = agent_analysis.get('task_details')
            if task_details and task_details.get('tasks'):
                for task in task_details['tasks']:
                    if task.get('due_date'):
                        suggestions.append("📅 Set deadline reminder")
                        break
        
        # Check urgency and priority
        urgency = agent_analysis.get('urgency', 'medium')
        priority = agent_analysis.get('priority', 'medium')
        
        if urgency in ['high', 'critical'] or priority == 'high':
            suggestions.append("🚨 Mark as high priority")
            
        if urgency == 'critical':
            suggestions.append("⚡ Requires immediate attention")
        
        # Check primary type
        primary_type = agent_analysis.get('primary_type')
        if primary_type == 'urgent':
            suggestions.append("⚡ Handle urgently")
        elif primary_type == 'informational':
            suggestions.append("📖 File for reference")
        elif primary_type == 'promotional':
            suggestions.append("🗑️ Consider archiving")
        
        # Check specific recommendations from agent
        agent_recommendations = agent_analysis.get('recommendations', [])
        for rec in agent_recommendations:
            if rec == 'create_calendar_event' and "📅 Create calendar event" not in suggestions:
                suggestions.append("📅 Create calendar event")
            elif rec == 'add_to_task_list' and "✅ Add to task list" not in suggestions:
                suggestions.append("✅ Add to task list")
            elif rec == 'mark_priority' and "🚨 Mark as high priority" not in suggestions:
                suggestions.append("🚨 Mark as high priority")
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        # Add default if no suggestions
        if not unique_suggestions:
            unique_suggestions.append("📧 No specific action needed")
        
        print(f"💡 Generated {len(unique_suggestions)} suggestions: {unique_suggestions}")
        
        return unique_suggestions

