import os
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import numpy as np
from email.utils import parsedate_to_datetime

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class EmailProcessor:
    def __init__(self):
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")
        self.embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-ada-002")
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * 1536  # Return zero vector if error
    
    def summarize_email(self, content: str, subject: str = "") -> str:
        """Generate a concise summary of email content"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert email analyzer. Create a concise, actionable summary of the email.
            Focus on:
            - Main purpose/topic
            - Key information
            - Action items or requests
            - Important dates/deadlines
            - Sentiment (urgent, casual, formal, etc.)
            
            Keep it under 3 sentences."""),
            ("human", "Subject: {subject}\n\nEmail Content:\n{content}")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"subject": subject, "content": content})
    
    def extract_action_items(self, content: str) -> str:
        """Extract action items from email"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract action items from this email. Look for:
            - Tasks to be completed
            - Deadlines
            - Meetings to schedule
            - Information to provide
            - Decisions to make
            
            Return as a bulleted list. If no action items, return 'None'."""),
            ("human", "Email content:\n{content}")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"content": content})
    
    def categorize_email(self, subject: str, content: str) -> str:
        """Categorize email content"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Categorize this email into ONE of these categories:
            - work: Professional, business-related
            - personal: Personal communications
            - promotional: Marketing, advertisements, deals
            - financial: Bills, banking, investments
            - travel: Bookings, confirmations, itineraries
            - social: Social media, events, invitations
            - automated: System notifications, receipts
            - education: Learning, courses, academic
            - other: Anything else
            
            Respond with only the category name."""),
            ("human", "Subject: {subject}\nContent: {content}")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"subject": subject, "content": content}).strip().lower()
    
    def analyze_sentiment(self, content: str) -> str:
        """Analyze email sentiment"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze the sentiment of this email. Respond with ONE word:
            - positive: Happy, excited, appreciative, congratulatory
            - negative: Angry, disappointed, complaint, urgent problem
            - neutral: Informational, professional, routine
            - urgent: Time-sensitive, requires immediate attention"""),
            ("human", "Email content:\n{content}")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"content": content}).strip().lower()
    
    def determine_priority(self, subject: str, content: str, sender: str) -> str:
        """Determine email priority"""
        # Check for urgency keywords
        urgent_keywords = ['urgent', 'asap', 'emergency', 'immediate', 'deadline', 'due today']
        high_keywords = ['important', 'priority', 'meeting', 'call me', 'review']
        
        text_to_check = f"{subject} {content}".lower()
        
        if any(keyword in text_to_check for keyword in urgent_keywords):
            return 'high'
        elif any(keyword in text_to_check for keyword in high_keywords):
            return 'medium'
        elif 'noreply' in sender.lower() or 'no-reply' in sender.lower():
            return 'low'
        else:
            return 'medium'
    
    def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete email and return analysis"""
        subject = email_data.get('subject', '')
        content = email_data.get('content', '')
        sender = email_data.get('sender', '')
        
        # Generate summary
        summary = self.summarize_email(content, subject)
        
        # Create embedding text (combine subject and summary for better searchability)
        embedding_text = f"{subject} {summary}"
        embedding = self.generate_embedding(embedding_text)
        
        # Extract additional information
        action_items = self.extract_action_items(content)
        category = self.categorize_email(subject, content)
        sentiment = self.analyze_sentiment(content)
        priority = self.determine_priority(subject, content, sender)
        
        return {
            'summary': summary,
            'embedding': embedding,
            'action_items': action_items,
            'category': category,
            'sentiment': sentiment,
            'priority': priority
        }
    
    def search_similar_emails(self, query: str, embeddings_db: List[tuple], top_k: int = 5) -> List[tuple]:
        """Find similar emails using vector similarity"""
        query_embedding = self.generate_embedding(query)
        
        similarities = []
        for email_id, email_embedding in embeddings_db:
            if email_embedding:
                # Calculate cosine similarity
                similarity = np.dot(query_embedding, email_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(email_embedding)
                )
                similarities.append((email_id, similarity))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]