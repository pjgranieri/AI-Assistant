import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.services.langchain_agent import EmailRouterAgent

def test_tool_chaining():
    """Test the enhanced agent with tool chaining"""
    print("🧪 Testing Enhanced LangChain Agent with Tool Chaining...")
    
    # Check if API key is loaded
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        print("Please add OPENAI_API_KEY=your_key_here to your .env file")
        return
    
    print(f"✅ Using OpenAI API key: {api_key[:8]}...{api_key[-4:]}")
    
    agent = EmailRouterAgent()
    
    # Test emails that should trigger different tool chains
    test_emails = [
        {
            "name": "Meeting Invitation",
            "subject": "Team Sprint Planning - Tomorrow 2 PM",
            "content": "Hi team, we have our sprint planning meeting tomorrow (Friday, Dec 8th) at 2:00 PM in Conference Room B. Please bring your user story estimates and any blockers. The meeting should last about 2 hours. Attendees: John, Sarah, Mike, Lisa.",
            "expected_tools": ["classify_email_type", "detect_event", "extract_event_details", "analyze_urgency"]
        },
        {
            "name": "Task Assignment",
            "subject": "URGENT: Code Review Required by EOD",
            "content": "Please review the PR #123 for the user authentication feature. This needs to be completed by end of day today as we have a deployment scheduled for tomorrow morning. The review should focus on security aspects and test coverage.",
            "expected_tools": ["classify_email_type", "detect_tasks", "extract_task_details", "analyze_urgency"]
        },
        {
            "name": "Mixed Event + Task",
            "subject": "Project Kickoff Meeting + Action Items",
            "content": "We're scheduling a project kickoff meeting for Monday 10 AM in the main conference room. Before the meeting, please complete the requirements document and send it to the team. Also, prepare a 5-minute presentation about your role in the project.",
            "expected_tools": ["classify_email_type", "detect_event", "extract_event_details", "detect_tasks", "extract_task_details", "analyze_urgency"]
        }
    ]
    
    for i, email in enumerate(test_emails, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {email['name']}")
        print(f"{'='*60}")
        print(f"Subject: {email['subject']}")
        print(f"Expected tools: {', '.join(email['expected_tools'])}")
        
        try:
            result = agent.analyze_email(
                subject=email['subject'],
                content=email['content']
            )
            
            print(f"\n✅ Analysis completed!")
            print(f"Primary Type: {result.get('primary_type')}")
            print(f"Contains Event: {result.get('contains_event')}")
            print(f"Contains Tasks: {result.get('contains_tasks')}")
            print(f"Urgency: {result.get('urgency')}")
            print(f"Priority: {result.get('priority')}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")
            print(f"Tool Chain Used: {result.get('tool_chain_used', False)}")
            
            print(f"\n🔍 Debug Info:")
            print(f"  Tool Chain Used: {result.get('tool_chain_used', False)}")
            print(f"  Tools Executed: {result.get('tools_executed', [])}")
            print(f"  Raw Confidence: {result.get('confidence', 0)}")
            print(f"  Raw Recommendations: {result.get('recommendations', [])}")
            
            if result.get('event_details'):
                print(f"\n📅 Event Details:")
                event = result['event_details']
                print(f"  Title: {event.get('title')}")
                print(f"  DateTime: {event.get('datetime')}")
                print(f"  Location: {event.get('location')}")
                print(f"  Duration: {event.get('duration_minutes')} minutes")
            
            if result.get('task_details') and result['task_details'].get('tasks'):
                print(f"\n✅ Task Details:")
                for task in result['task_details']['tasks']:
                    print(f"  - {task.get('title')} (Priority: {task.get('priority')})")
                    if task.get('due_date'):
                        print(f"    Due: {task.get('due_date')}")
            
            print(f"\n💡 Recommendations: {', '.join(result.get('recommendations', []))}")
            print(f"🤔 Reasoning: {result.get('reasoning', '')[:200]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def test_simple_classification():
    """Test simple classification without LangChain (faster for debugging)"""
    print("\n🔧 Testing Simple Classification (No API calls)...")
    
    agent = EmailRouterAgent()
    
    simple_tests = [
        ("Meeting Tomorrow", "Team meeting at 2 PM tomorrow"),
        ("URGENT Task", "Please complete this by EOD"),
        ("Newsletter", "Monthly company newsletter with updates")
    ]
    
    for subject, content in simple_tests:
        result = agent._create_fallback_analysis(subject, content)
        print(f"\nSubject: {subject}")
        print(f"Type: {result['primary_type']}")
        print(f"Event: {result['contains_event']}")
        print(f"Task: {result['contains_tasks']}")

if __name__ == "__main__":
    # Test simple classification first (no API calls)
    test_simple_classification()
    
    # Then test full LangChain agent (requires API)
    test_tool_chaining()
    print("\n🎉 Enhanced agent testing completed!")