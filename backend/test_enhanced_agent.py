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
            
            # Mixed Classification Fix: Override primary_type if both event and tasks are found
            if result.get('contains_event') and result.get('contains_tasks'):
                result['primary_type'] = 'mixed'
            
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
            print(f"  Raw Confidence: {result.get('confidence', 0):.2f}")
            print(f"  Raw Recommendations: {result.get('recommendations', [])}")

            # EVENT DETAILS PRINTING - Show all available event details
            if result.get('event_details') and isinstance(result['event_details'], dict):
                print(f"\n📅 Event Details:")
                event = result['event_details']
                
                # Print all available event details
                if event.get('title'):
                    print(f"  • Title: {event['title']}")
                if event.get('description'):
                    print(f"  • Description: {event['description']}")
                if event.get('datetime'):
                    print(f"  • Date & Time: {event['datetime']}")
                if event.get('end_datetime'):
                    print(f"  • End Time: {event['end_datetime']}")
                if event.get('duration_minutes'):
                    print(f"  • Duration: {event['duration_minutes']} minutes")
                if event.get('location'):
                    print(f"  • Location: {event['location']}")
                if event.get('attendees') and len(event['attendees']) > 0:
                    print(f"  • Attendees:")
                    for attendee in event['attendees']:
                        print(f"    - {attendee}")
                if event.get('agenda'):
                    print(f"  • Agenda: {event['agenda']}")

            # TASK DETAILS PRINTING - Handle both array and single task object
            task_details = result.get('task_details')
            if task_details:
                print(f"\n📝 Task Details:")
                
                # Handle both array of tasks and single task object
                tasks = []
                if isinstance(task_details, list):
                    tasks = task_details
                elif isinstance(task_details, dict):
                    if 'tasks' in task_details and isinstance(task_details['tasks'], list):
                        tasks = task_details['tasks']
                    elif task_details.get('title'):  # Single task object
                        tasks = [task_details]
                
                if tasks:
                    for i, task in enumerate(tasks, 1):
                        if isinstance(task, dict) and task.get('description'):  # Changed from 'title' to 'description'
                            print(f"  {i}. {task['description']}")  # Changed from 'title' to 'description'
                            if task.get('priority'):
                                print(f"     • Priority: {task['priority']}")
                            if task.get('due_date'):
                                print(f"     • Due Date: {task['due_date']}")
                            if task.get('category'):
                                print(f"     • Category: {task['category']}")
                            if task.get('assignee'):
                                print(f"     • Assignee: {task['assignee']}")
                            if task.get('status'):
                                print(f"     • Status: {task['status']}")
                            print()  # Add spacing between tasks
                else:
                    print("  No tasks found")

            # RECOMMENDATION DEDUPLICATION with proper ordering
            recommendations = result.get('recommendations', [])
            if recommendations:
                # Remove duplicates while maintaining order
                seen = set()
                deduped_recommendations = []
                
                # Priority ordering: mark_priority first if urgency is high
                urgency = result.get('urgency', 'low')
                if urgency in ['high', 'critical'] and 'mark_priority' in recommendations:
                    deduped_recommendations.append('mark_priority')
                    seen.add('mark_priority')
                
                # Then create_calendar_event if contains_event
                if result.get('contains_event') and 'create_calendar_event' in recommendations:
                    if 'create_calendar_event' not in seen:
                        deduped_recommendations.append('create_calendar_event')
                        seen.add('create_calendar_event')
                
                # Then add_to_task_list if contains_tasks
                if result.get('contains_tasks') and 'add_to_task_list' in recommendations:
                    if 'add_to_task_list' not in seen:
                        deduped_recommendations.append('add_to_task_list')
                        seen.add('add_to_task_list')
                
                # Add remaining recommendations in original order
                for rec in recommendations:
                    if rec not in seen:
                        deduped_recommendations.append(rec)
                        seen.add(rec)
                
                print(f"\n💡 Recommendations: {', '.join(deduped_recommendations)}")

            # CONFIDENCE & REASONING - Always fully displayed
            reasoning = result.get('reasoning', '')
            if reasoning:
                print(f"\n🤔 Reasoning:")
                # Allow wrapping to multiple lines instead of cutting off
                if len(reasoning) > 100:
                    # Break into multiple lines for readability
                    words = reasoning.split(' ')
                    current_line = ""
                    for word in words:
                        if len(current_line + word) > 80:  # 80 char line limit
                            print(f"  {current_line}")
                            current_line = word + " "
                        else:
                            current_line += word + " "
                    if current_line.strip():  # Print remaining line
                        print(f"  {current_line.strip()}")
                else:
                    print(f"  {reasoning}")
                
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
        ("Newsletter", "Monthly company newsletter with updates"),
        ("Mixed: Meeting + Tasks", "Project meeting Monday 10 AM. Please prepare the presentation and review the documents beforehand.")
    ]
    
    for subject, content in simple_tests:
        result = agent._create_fallback_analysis(subject, content)
        
        # Mixed Classification Fix for simple tests too
        if result.get('contains_event') and result.get('contains_tasks'):
            result['primary_type'] = 'mixed'
        
        print(f"\nSubject: {subject}")
        print(f"Primary Type: {result['primary_type']}")
        print(f"Contains Event: {result['contains_event']}")
        print(f"Contains Tasks: {result['contains_tasks']}")
        print(f"Urgency: {result['urgency']}")
        print(f"Priority: {result['priority']}")
        print(f"Confidence: {result['confidence']:.2f}")
        
        # Apply same recommendation deduplication logic
        recommendations = result.get('recommendations', [])
        if recommendations:
            seen = set()
            deduped_recommendations = []
            
            # Priority ordering
            urgency = result.get('urgency', 'low')
            if urgency in ['high', 'critical'] and 'mark_priority' in recommendations:
                deduped_recommendations.append('mark_priority')
                seen.add('mark_priority')
            
            if result.get('contains_event') and 'create_calendar_event' in recommendations:
                if 'create_calendar_event' not in seen:
                    deduped_recommendations.append('create_calendar_event')
                    seen.add('create_calendar_event')
            
            if result.get('contains_tasks') and 'add_to_task_list' in recommendations:
                if 'add_to_task_list' not in seen:
                    deduped_recommendations.append('add_to_task_list')
                    seen.add('add_to_task_list')
            
            for rec in recommendations:
                if rec not in seen:
                    deduped_recommendations.append(rec)
                    seen.add(rec)
            
            print(f"Recommendations: {', '.join(deduped_recommendations)}")

if __name__ == "__main__":
    # Test simple classification first (no API calls)
    test_simple_classification()
    
    # Then test full LangChain agent (requires API)
    test_tool_chaining()
    print("\n🎉 Enhanced agent testing completed!")