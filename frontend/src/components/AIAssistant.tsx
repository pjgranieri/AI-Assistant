import React, { useState } from 'react'

interface EnhancedEmailAnalysis {
  summary: string
  suggestions?: string[]
  primary_type?: string
  contains_event?: boolean
  contains_tasks?: boolean
  urgency?: string
  priority?: string
  event_details?: any
  task_details?: { tasks?: Array<any> }
  recommendations?: string[]
  confidence?: number
  reasoning?: string
  tool_chain_used?: boolean
}

export default function AIAssistant() {
  const [content, setContent] = useState('')
  const [subject, setSubject] = useState('')
  const [analysis, setAnalysis] = useState<EnhancedEmailAnalysis | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSummarize = async () => {
    if (!content.trim()) return
    setLoading(true)
    try {
      const resp = await fetch('http://localhost:8000/ai/summarize-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject: subject || '(No Subject)',
            content,
          sender: 'you@example.com'
        })
      })
      if (!resp.ok) throw new Error('Request failed')
      const data: EnhancedEmailAnalysis = await resp.json()
      setAnalysis(data)
    } catch (e) {
      setAnalysis({ summary: 'Error performing analysis.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ai-assistant-section">
      <h2>AI Assistant</h2>

      <input
        placeholder="Subject (optional)"
        value={subject}
        onChange={(e)=>setSubject(e.target.value)}
        style={{ width:'100%', marginBottom:8, padding:8 }}
      />
      <textarea
        value={content}
        onChange={(e)=>setContent(e.target.value)}
        placeholder="Paste email or text..."
        rows={5}
        style={{ width:'100%', padding:8 }}
      />
      <button onClick={handleSummarize} disabled={loading || !content.trim()}>
        {loading ? 'Analyzing...' : 'Analyze Email'}
      </button>

      {analysis && (
        <div style={{ marginTop:20 }}>
          <h3>Summary</h3>
          <p>{analysis.summary}</p>

            <details open>
            <summary>Classification</summary>
            <p>
              Type: {analysis.primary_type || '-'} |
              Event: {String(analysis.contains_event)} |
              Tasks: {String(analysis.contains_tasks)}
            </p>
            <p>
              Urgency: {analysis.urgency || '-'} |
              Priority: {analysis.priority || '-'} |
              Confidence: {analysis.confidence?.toFixed(2) || '-'}
            </p>
          </details>

          {analysis.event_details && (
            <details style={{ marginTop:10 }}>
              <summary>Event Details</summary>
              <pre style={{ whiteSpace:'pre-wrap' }}>{JSON.stringify(analysis.event_details, null, 2)}</pre>
            </details>
          )}

          {analysis.task_details?.tasks && analysis.task_details.tasks.length > 0 && (
            <details style={{ marginTop:10 }}>
              <summary>Task Details</summary>
              <ul>
                {analysis.task_details.tasks.map((t,i)=>(
                  <li key={i}>{t.description || JSON.stringify(t)}</li>
                ))}
              </ul>
            </details>
          )}

          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <details style={{ marginTop:10 }}>
              <summary>Recommendations</summary>
              <ul>
                {analysis.recommendations.map(r => <li key={r}>{r}</li>)}
              </ul>
            </details>
          )}

          {analysis.reasoning && (
            <details style={{ marginTop:10 }}>
              <summary>Reasoning</summary>
              <p style={{ whiteSpace:'pre-wrap' }}>{analysis.reasoning}</p>
            </details>
          )}
        </div>
      )}

      {analysis && (
        <div style={{ marginTop:8, fontSize:12, opacity:0.7 }}>
          Mode: {analysis.tool_chain_used ? 'Agent (tool chain)' : 'Fallback'}
        </div>
      )}
    </div>
  )
}