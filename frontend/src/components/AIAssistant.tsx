import React, { useState } from 'react'

interface SummaryResponse {
  summary: string
  suggestions?: string
}

interface DailyBriefResponse {
  date: string
  events_count: number
  schedule_summary: string
  suggestions: string
  events: Array<{
    title: string
    description: string
    datetime: string
  }>
}

export default function AIAssistant() {
  const [content, setContent] = useState('')
  const [contentType, setContentType] = useState('general')
  const [summary, setSummary] = useState<SummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSummarize = async () => {
    if (!content.trim()) return
    
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/ai/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          content_type: contentType,
        }),
      })
      
      if (response.ok) {
        const data = await response.json()
        setSummary(data)
      } else {
        console.error('Summarization failed')
        setSummary({
          summary: 'Sorry, I encountered an error while analyzing your content. Please try again.',
        })
      }
    } catch (error) {
      console.error('Error:', error)
      setSummary({
        summary: 'Sorry, I could not connect to the AI service. Please check if the backend is running.',
      })
    } finally {
      setLoading(false)
    }
  }

  const getDailyBrief = async () => {
    setLoading(true)
    try {
      const today = new Date().toISOString().split('T')[0]
      const response = await fetch(`http://localhost:8000/ai/daily-brief?date=${today}`)
      
      if (response.ok) {
        const data: DailyBriefResponse = await response.json()
        setSummary({
          summary: data.schedule_summary,
          suggestions: data.suggestions
        })
      } else {
        console.error('Daily brief failed')
        setSummary({
          summary: 'Sorry, I could not generate your daily brief. Please try again.',
        })
      }
    } catch (error) {
      console.error('Error:', error)
      setSummary({
        summary: 'Sorry, I could not connect to the AI service. Please check if the backend is running.',
      })
    } finally {
      setLoading(false)
    }
  }

  const getCalendarSummary = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/ai/summarize-calendar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          include_suggestions: true
        }),
      })
      
      if (response.ok) {
        const data = await response.json()
        setSummary(data)
      } else {
        console.error('Calendar summary failed')
        setSummary({
          summary: 'Sorry, I could not analyze your calendar. Please try again.',
        })
      }
    } catch (error) {
      console.error('Error:', error)
      setSummary({
        summary: 'Sorry, I could not connect to the AI service. Please check if the backend is running.',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ai-assistant-section">
      <h2>AI Assistant</h2>
      
      <div className="content-input">
        <select 
          value={contentType} 
          onChange={(e) => setContentType(e.target.value)}
          className="content-type-select"
        >
          <option value="general">General Content</option>
          <option value="email">Email</option>
        </select>
        
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste your content here for AI analysis..."
          rows={4}
          className="content-textarea"
        />
        
        <div className="action-buttons">
          <button 
            onClick={handleSummarize} 
            disabled={loading || !content.trim()}
            className="summarize-btn"
          >
            {loading ? 'Analyzing...' : 'Analyze Text'}
          </button>
          
          <button 
            onClick={getDailyBrief} 
            disabled={loading}
            className="daily-brief-btn"
          >
            {loading ? 'Loading...' : 'Daily Brief'}
          </button>
          
          <button 
            onClick={getCalendarSummary} 
            disabled={loading}
            className="calendar-summary-btn"
          >
            {loading ? 'Loading...' : 'Calendar Summary'}
          </button>
        </div>
      </div>

      {summary && (
        <div className="summary-result">
          <h3>AI Analysis</h3>
          <div className="summary-content">
            <h4>Summary:</h4>
            <p>{summary.summary}</p>
          </div>
          
          {summary.suggestions && (
            <div className="suggestions-content">
              <h4>Suggestions:</h4>
              <p>{summary.suggestions}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}