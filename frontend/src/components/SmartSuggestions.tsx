import React, { useState } from 'react'

interface SmartSuggestionsProps {
  emailId: number
  suggestions: string[]
  agentAnalysis: any
}

export default function SmartSuggestions({ emailId, suggestions, agentAnalysis }: SmartSuggestionsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleCreateEvent = async () => {
    if (!agentAnalysis.event_details) return
    
    setIsLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/smart-email/create-from-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: agentAnalysis.event_details.title,
          content: agentAnalysis.event_details.description,
          sender: agentAnalysis.sender
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        alert(`Created ${result.events.length} events and ${result.tasks.length} tasks!`)
      }
    } catch (error) {
      console.error('Failed to create items:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="smart-suggestions">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="suggestions-toggle"
      >
        🤖 Smart Suggestions ({suggestions.length})
      </button>
      
      {isExpanded && (
        <div className="suggestions-content">
          <div className="analysis-type">
            <strong>Type:</strong> {agentAnalysis.primary_type}
            <span className="confidence">
              (Confidence: {(agentAnalysis.confidence * 100).toFixed(0)}%)
            </span>
          </div>
          
          <div className="suggestions-list">
            {suggestions.map((suggestion, index) => (
              <div key={index} className="suggestion-item">
                {suggestion}
                {suggestion.includes('calendar') && (
                  <button 
                    onClick={handleCreateEvent}
                    disabled={isLoading}
                    className="create-event-btn"
                  >
                    {isLoading ? '⏳' : '📅'} Create Event
                  </button>
                )}
              </div>
            ))}
          </div>
          
          {agentAnalysis.event_details && (
            <div className="event-preview">
              <h4>🗓️ Detected Event:</h4>
              <p><strong>Title:</strong> {agentAnalysis.event_details.title}</p>
              <p><strong>Date:</strong> {agentAnalysis.event_details.datetime || 'Not specified'}</p>
              <p><strong>Location:</strong> {agentAnalysis.event_details.location || 'Not specified'}</p>
            </div>
          )}
          
          {agentAnalysis.task_details && agentAnalysis.task_details.tasks && (
            <div className="tasks-preview">
              <h4>✅ Detected Tasks:</h4>
              {agentAnalysis.task_details.tasks.map((task: any, index: number) => (
                <div key={index} className="task-item">
                  <strong>{task.title}</strong>
                  {task.due_date && <span> (Due: {task.due_date})</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}