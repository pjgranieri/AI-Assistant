import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class ContentSummarizer:
    def __init__(self):
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")
    
    def summarize_email(self, email_content: str, subject: str = "") -> str:
        """Summarize email content"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that summarizes emails concisely. Focus on key points, action items, and important dates."),
            ("human", "Subject: {subject}\n\nEmail Content:\n{content}\n\nProvide a concise summary:")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"subject": subject, "content": email_content})
    
    def summarize_calendar_events(self, events: List[Dict[str, Any]]) -> str:
        """Summarize a list of calendar events"""
        events_text = "\n".join([
            f"- {event.get('title', 'Untitled')} on {event.get('datetime', 'No date')} - {event.get('description', 'No description')}"
            for event in events
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that summarizes calendar events. Provide insights about the schedule, time conflicts, and important meetings."),
            ("human", "Here are the upcoming events:\n{events}\n\nProvide a helpful summary:")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"events": events_text})
    
    def summarize_daily_schedule(self, date: str, events: List[Dict[str, Any]]) -> str:
        """Summarize events for a specific day"""
        events_text = "\n".join([
            f"{event.get('datetime', 'No time')}: {event.get('title', 'Untitled')} - {event.get('description', '')}"
            for event in events
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that provides daily schedule summaries. Be concise and highlight important meetings or deadlines."),
            ("human", "Schedule for {date}:\n{events}\n\nProvide a brief daily summary:")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"date": date, "events": events_text})
    
    def generate_smart_suggestions(self, context: str) -> str:
        """Generate smart suggestions based on content"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant that provides helpful suggestions and insights. Analyze the content and provide actionable recommendations."),
            ("human", "Based on this information:\n{context}\n\nProvide helpful suggestions:")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"context": context})

# Legacy function for backward compatibility
def summarize_text(text: str) -> str:
    summarizer = ContentSummarizer()
    return summarizer.generate_smart_suggestions(text)