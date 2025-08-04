import React, { useState, useEffect } from 'react'

interface EmailSummary {
  id: number
  subject: string
  sender: string
  summary: string
  category: string
  priority: string
  sentiment: string
  action_items: string
  received_at: string
}

interface EmailAnalytics {
  categories: Array<{ category: string; count: number }>
  priorities: Array<{ priority: string; count: number }>
  sentiments: Array<{ sentiment: string; count: number }>
}

export default function EmailDashboard() {
  const [emails, setEmails] = useState<EmailSummary[]>([])
  const [analytics, setAnalytics] = useState<EmailAnalytics | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<EmailSummary[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadEmails()
    loadAnalytics()
  }, [])

  const loadEmails = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/emails?user_id=test_user&limit=20')
      if (response.ok) {
        const data = await response.json()
        setEmails(data)
      }
    } catch (error) {
      console.error('Failed to load emails:', error)
    }
  }

  const loadAnalytics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/emails/analytics/test_user?days=30')
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Failed to load analytics:', error)
    }
  }

  const searchEmails = async () => {
    if (!searchQuery.trim()) return
    
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/emails/search?user_id=test_user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: 10
        })
      })
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data)
      }
    } catch (error) {
      console.error('Search failed:', error)
    }
    setLoading(false)
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#ff4444'
      case 'medium': return '#ffaa00'
      case 'low': return '#44ff44'
      default: return '#888'
    }
  }

  return (
    <div style={{ padding: '20px', color: 'white' }}>
      <h1>📧 Email Dashboard</h1>
      
      {/* Analytics Section */}
      {analytics && (
        <div style={{ marginBottom: '30px', display: 'flex', gap: '20px' }}>
          <div style={{ background: '#333', padding: '15px', borderRadius: '8px', flex: 1 }}>
            <h3>Categories</h3>
            {analytics.categories.map(cat => (
              <div key={cat.category} style={{ marginBottom: '5px' }}>
                {cat.category}: {cat.count}
              </div>
            ))}
          </div>
          <div style={{ background: '#333', padding: '15px', borderRadius: '8px', flex: 1 }}>
            <h3>Priorities</h3>
            {analytics.priorities.map(pri => (
              <div key={pri.priority} style={{ marginBottom: '5px', color: getPriorityColor(pri.priority) }}>
                {pri.priority}: {pri.count}
              </div>
            ))}
          </div>
          <div style={{ background: '#333', padding: '15px', borderRadius: '8px', flex: 1 }}>
            <h3>Sentiments</h3>
            {analytics.sentiments.map(sent => (
              <div key={sent.sentiment} style={{ marginBottom: '5px' }}>
                {sent.sentiment}: {sent.count}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search Section */}
      <div style={{ marginBottom: '30px' }}>
        <h2>🔍 Semantic Search</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search emails by meaning (e.g., 'urgent work tasks', 'social events')"
            style={{ 
              flex: 1, 
              padding: '10px', 
              background: '#444', 
              color: 'white', 
              border: '1px solid #666',
              borderRadius: '4px'
            }}
            onKeyPress={(e) => e.key === 'Enter' && searchEmails()}
          />
          <button 
            onClick={searchEmails} 
            disabled={loading}
            style={{ 
              padding: '10px 20px', 
              background: '#0066cc', 
              color: 'white', 
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
        
        {searchResults.length > 0 && (
          <div>
            <h3>Search Results:</h3>
            {searchResults.map(email => (
              <EmailCard key={`search-${email.id}`} email={email} />
            ))}
          </div>
        )}
      </div>

      {/* All Emails Section */}
      <div>
        <h2>📨 All Emails ({emails.length})</h2>
        {emails.map(email => (
          <EmailCard key={email.id} email={email} />
        ))}
      </div>
    </div>
  )
}

function EmailCard({ email }: { email: EmailSummary }) {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return '#ff4444'
      case 'medium': return '#ffaa00'
      case 'low': return '#44ff44'
      default: return '#888'
    }
  }

  return (
    <div style={{ 
      background: '#333', 
      margin: '10px 0', 
      padding: '15px', 
      borderRadius: '8px',
      borderLeft: `4px solid ${getPriorityColor(email.priority)}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div style={{ flex: 1 }}>
          <h4 style={{ margin: '0 0 5px 0' }}>{email.subject}</h4>
          <p style={{ margin: '0 0 10px 0', color: '#ccc', fontSize: '0.9em' }}>
            From: {email.sender}
          </p>
          <p style={{ margin: '0 0 10px 0' }}>{email.summary}</p>
          {email.action_items && email.action_items !== 'None' && (
            <div style={{ background: '#444', padding: '8px', borderRadius: '4px', marginTop: '10px' }}>
              <strong>Action Items:</strong>
              <div style={{ marginTop: '5px' }}>{email.action_items}</div>
            </div>
          )}
        </div>
        <div style={{ marginLeft: '15px', textAlign: 'right', fontSize: '0.8em' }}>
          <div style={{ marginBottom: '5px' }}>
            <span style={{ 
              background: email.category === 'work' ? '#0066cc' : 
                          email.category === 'personal' ? '#00cc66' : 
                          email.category === 'promotional' ? '#cc6600' : '#666',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '0.8em'
            }}>
              {email.category}
            </span>
          </div>
          <div style={{ color: getPriorityColor(email.priority) }}>
            {email.priority} priority
          </div>
          <div style={{ color: '#999', marginTop: '5px' }}>
            {email.sentiment}
          </div>
        </div>
      </div>
    </div>
  )
}