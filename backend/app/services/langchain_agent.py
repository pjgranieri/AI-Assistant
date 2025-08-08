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
    
    for call, output in steps:
        name = getattr(call, "tool", None)
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
            
        elif name == "detect_event" and payload.get("contains_event"):
            out["contains_event"] = True
            conf = payload.get("confidence", 0.8)
            confidences.append(conf)
            if "create_calendar_event" not in out["recommendations"]:
                out["recommendations"].append("create_calendar_event")
            reasoning_parts.append(f"Event detected ({conf:.2f})")
            
        elif name == "extract_event_details":
            out["event_details"] = payload
            reasoning_parts.append("Event details extracted")
            
        elif name == "detect_tasks" and payload.get("contains_tasks"):
            out["contains_tasks"] = True
            conf = payload.get("confidence", 0.8)
            confidences.append(conf)
            if "add_to_task_list" not in out["recommendations"]:
                out["recommendations"].append("add_to_task_list")
            reasoning_parts.append(f"Tasks detected ({conf:.2f})")
            
        elif name == "extract_task_details":
            out["task_details"] = payload
            reasoning_parts.append("Task details extracted")
            
        elif name == "analyze_urgency":
            out["urgency"] = payload.get("urgency", out["urgency"])
            out["priority"] = payload.get("priority", out["priority"])
            confidences.append(0.8)
            reasoning_parts.append(f"Urgency: {out['urgency']}, Priority: {out['priority']}")
    
    # Apply recommendation rules
    if out["contains_event"] and "create_calendar_event" not in out["recommendations"]:
        out["recommendations"].append("create_calendar_event")
    if out["contains_tasks"] and "add_to_task_list" not in out["recommendations"]:
        out["recommendations"].append("add_to_task_list")
    if out["urgency"] in ["high", "critical"] and "mark_priority" not in out["recommendations"]:
        out["recommendations"].append("mark_priority")
    
    # Deduplicate recommendations
    out["recommendations"] = list(dict.fromkeys(out["recommendations"]))
    
    # Calculate confidence as max of tool confidences
    out["confidence"] = max(confidences) if confidences else 0.5
    out["reasoning"] = "; ".join(reasoning_parts) if reasoning_parts else "Aggregated from tool steps"
    
    print(f"📊 Aggregated result: {out['primary_type']}, event={out['contains_event']}, tasks={out['contains_tasks']}")
    print(f"💡 Recommendations: {out['recommendations']}")
    
    return out

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
                json.loads(result)
                return result
            except:
                return json.dumps({"title": None, "description": None, "datetime": None, "end_datetime": None, "location": None, "attendees": [], "duration_minutes": None, "agenda": None})
        
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
                Return only valid JSON with a tasks array containing objects with fields:
                title, description, priority, due_date, assignee, status, category"""),
                ("human", "Email: {content}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            result = chain.invoke({"content": email_content})
            
            try:
                json.loads(result)
                return result
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
            ("system", """You are an intelligent email routing agent that uses specialized tools to analyze emails.

Your workflow:
1. First, classify the email type using classify_email_type
2. Based on the type, use appropriate tools:
   - If potentially an event: use detect_event, then extract_event_details if needed
   - If potentially a task: use detect_tasks, then extract_task_details if needed
   - For all emails: use analyze_urgency to determine priority
3. Combine all tool results into a comprehensive analysis

CRITICAL: After using all necessary tools, output **only** one JSON object with these exact keys:
{{
    "primary_type": "event|task|informational|promotional|automated|personal|urgent",
    "contains_event": true/false,
    "contains_tasks": true/false,
    "urgency": "low|medium|high|critical",
    "priority": "low|medium|high",
    "event_details": {{...}} or null,
    "task_details": {{...}} or null,
    "recommendations": ["create_calendar_event", "add_to_task_list", "mark_priority", "no_action"],
    "confidence": 0.0-1.0,
    "reasoning": "step-by-step analysis explanation"
}}

Do not include any prose outside the JSON. Only return the JSON object."""),
            ("human", "Analyze this email:\n\n{input}"),
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
            max_iterations=6
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
            
            # Apply recommendation rules to ensure consistency
            recommendations = final_analysis.get("recommendations", [])
            if final_analysis.get("contains_event") and "create_calendar_event" not in recommendations:
                recommendations.append("create_calendar_event")
            if final_analysis.get("contains_tasks") and "add_to_task_list" not in recommendations:
                recommendations.append("add_to_task_list")
            if final_analysis.get("urgency") in ["high", "critical"] and "mark_priority" not in recommendations:
                recommendations.append("mark_priority")
            
            # Remove duplicates and update
            final_analysis["recommendations"] = list(dict.fromkeys(recommendations))
            
            # Add metadata
            final_analysis['sender'] = sender
            final_analysis['processed_at'] = dt.datetime.utcnow().isoformat()
            final_analysis['tool_chain_used'] = tool_chain_used
            final_analysis['tools_executed'] = tools_executed
            
            return final_analysis
            
        except Exception as e:
            print(f"Error in agent analysis: {e}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_analysis(subject, content, str(e))
    
    def _create_fallback_analysis(self, subject: str, content: str, error: str = None) -> Dict[str, Any]:
        """Create a basic analysis if the agent fails"""
        
        # Use better simple classification
        primary_type = self._classify_email_simple(subject, content)
        contains_event = self._detect_event_simple(subject, content)
        contains_tasks = self._detect_task_simple(subject, content)
        
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
        
        # Better recommendations for fallback
        recommendations = []
        if contains_event:
            recommendations.append("create_calendar_event")
        if contains_tasks:
            recommendations.append("add_to_task_list")
        if urgency in ['high', 'critical']:
            recommendations.append("mark_priority")
        if not recommendations:
            recommendations.append("no_action")
        
        return {
            "primary_type": primary_type,
            "contains_event": contains_event,
            "contains_tasks": contains_tasks,
            "urgency": urgency,
            "priority": priority,
            "event_details": None,
            "task_details": None,
            "recommendations": recommendations,
            "confidence": 0.6,  # Higher confidence for fallback
            "reasoning": f"Fallback analysis used{': ' + error if error else ''} - {primary_type} type detected",
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

