import os
import re
import datetime as dt
from typing import List, Dict, Any, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import numpy as np
from email.utils import parsedate_to_datetime

from app.db.models.email_summary import EmailSummary
from langchain.schema import HumanMessage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class EmailProcessor:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)  # Use cheaper model
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")  # Use smaller embedding model
        self.processing_costs = {
            "gpt-3.5-turbo": 0.0005,  # per 1K tokens
            "text-embedding-3-small": 0.00002  # per 1K tokens
        }
    
    def calculate_cost(self, text: str, operation: str) -> float:
        """Estimate processing cost"""
        token_count = len(text.split()) * 1.3  # Rough token estimation
        if operation == "summary":
            return (token_count / 1000) * self.processing_costs["gpt-3.5-turbo"]
        elif operation == "embedding":
            return (token_count / 1000) * self.processing_costs["text-embedding-3-small"]
        return 0.0
    
    def needs_reprocessing(self, email_data: Dict[str, Any], existing_summary: Optional[EmailSummary]) -> bool:
        """Check if email needs reprocessing"""
        if not existing_summary:
            return True
        
        # Only reprocess if content changed significantly
        if existing_summary.content != email_data.get('content', ''):
            return True
            
        # Don't reprocess if recently processed
        if existing_summary.last_processed and \
           existing_summary.last_processed > dt.datetime.utcnow() - dt.timedelta(days=7):
            return False
            
        return False

    def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email with AI analysis"""
        content = email_data.get('content', '')
        subject = email_data.get('subject', '')
        
        # Truncate content if too long (keep first 10k characters)
        max_content_length = 10000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [Content truncated for processing]"
            print(f"Truncated long email content from {len(email_data.get('content', ''))} to {len(content)} characters")
        
        # Create prompt for analysis
        prompt = f"""
        Analyze this email and provide:
        1. A concise summary (2-3 sentences)
        2. Sentiment (positive/negative/neutral)
        3. Priority (high/medium/low) - Note: promotional emails should be medium at most
        4. Category (work/personal/promotional/financial/travel/other)
        5. Action items (if any)

        Subject: {subject}
        Content: {content}

        Respond in this exact format:
        Summary: [summary]
        Sentiment: [sentiment]
        Priority: [priority]
        Category: [category]
        Action Items: [action items or "None"]
        """
        
        # Calculate estimated tokens (rough estimation)
        estimated_tokens = len(prompt.split()) * 1.3
        if estimated_tokens > 15000:  # Leave buffer for response
            print(f"Warning: Estimated tokens ({estimated_tokens}) still high after truncation")
        
        try:
            # Get AI analysis
            response = self.llm.invoke([HumanMessage(content=prompt)])
            analysis_text = response.content
            
            # Parse the response
            analysis = self._parse_analysis(analysis_text)
            
            # Generate embedding (use truncated content for embedding too)
            embedding_text = f"{subject} {content[:5000]}"  # Even shorter for embeddings
            embedding = self.embeddings.embed_query(embedding_text)
            analysis['embedding'] = embedding
            
            return analysis
            
        except Exception as e:
            print(f"Error processing email: {e}")
            # Return default values if processing fails
            return {
                'summary': f"Email from {email_data.get('sender', 'Unknown')} about {subject}",
                'sentiment': 'neutral',
                'priority': 'medium',
                'category': 'other',
                'action_items': 'None',
                'embedding': [0.0] * 1536  # Default embedding
            }
    
    def _parse_analysis(self, analysis_text: str) -> Dict[str, str]:
        """Parse AI analysis response"""
        lines = analysis_text.strip().split('\n')
        analysis = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'summary' in key:
                    analysis['summary'] = value
                elif 'sentiment' in key:
                    analysis['sentiment'] = value.lower()
                elif 'priority' in key:
                    analysis['priority'] = value.lower()
                elif 'category' in key:
                    analysis['category'] = value.lower()
                elif 'action' in key:
                    analysis['action_items'] = value
        
        # Ensure all required fields are present
        analysis.setdefault('summary', 'Email analysis failed')
        analysis.setdefault('sentiment', 'neutral')
        analysis.setdefault('priority', 'medium')
        analysis.setdefault('category', 'other')
        analysis.setdefault('action_items', 'None')
        
        return analysis
    
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