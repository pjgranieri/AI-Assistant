import React, { useState, useEffect } from 'react'
import GmailSync from './GmailSync'  // Add this import
import './EmailDashboard.css'

interface Email {
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

interface Analytics {
  period_days: number
  categories: { category: string; count: number }[]
  priorities: { priority: string; count: number }[]
  sentiments: { sentiment: string; count: number }[]
}

const EmailDashboard: React.FC = () => {
  console.log('EmailDashboard component rendering!') // Debug log
  
  const [emails, setEmails] = useState<Email[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Email[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'emails' | 'search' | 'analytics' | 'sync'>('emails')
  const [error, setError] = useState<string | null>(null) // Add error state

  const BASE_URL = 'http://localhost:8000'
  
  // Get user from localStorage or use test user
  const getUser = () => {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      const user = JSON.parse(savedUser)
      return user.id || user.user_id || 'test_user'
    }
    return 'test_user'
  }
  
  const USER_ID = getUser()
  console.log('Using USER_ID:', USER_ID) // Debug log

  useEffect(() => {
    console.log('EmailDashboard useEffect running...') // Debug log
    const loadData = async () => {
      await addTestData()
      await loadEmails()
      await loadAnalytics()
    }
    loadData()
  }, [])

  // Add event listener for email updates
  useEffect(() => {
    const handleEmailsUpdated = () => {
      loadEmails()  // Reload emails when sync completes
    }

    window.addEventListener('emailsUpdated', handleEmailsUpdated)
    return () => window.removeEventListener('emailsUpdated', handleEmailsUpdated)
  }, [])

  const addTestData = async () => {
    try {
      console.log('Adding test data for user:', USER_ID) // Debug log
      const response = await fetch(`${BASE_URL}/api/emails/test-data?user_id=${USER_ID}`, { 
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      const result = await response.json()
      console.log('Test data response:', result) // Debug log
    } catch (error) {
      console.error('Failed to add test data:', error)
      setError('Failed to add test data: ' + error.message)
    }
  }

  const loadEmails = async () => {
    try {
      console.log('Loading emails for user:', USER_ID) // Debug log
      const url = `${BASE_URL}/api/emails?user_id=${USER_ID}&limit=20`
      console.log('Fetching URL:', url) // Debug log
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      
      console.log('Emails response status:', response.status) // Debug log
      
      if (response.ok) {
        const data = await response.json()
        console.log('Emails data received:', data) // Debug log
        setEmails(data)
      } else {
        const errorText = await response.text()
        console.error('API Error:', response.status, errorText)
        setError(`Failed to load emails: ${response.status} - ${errorText}`)
      }
    } catch (error) {
      console.error('Failed to load emails:', error)
      setError('Failed to load emails: ' + error.message)
    }
  }

  const loadAnalytics = async () => {
    try {
      console.log('Loading analytics for user:', USER_ID) // Debug log
      const url = `${BASE_URL}/api/emails/analytics/${USER_ID}?days=30`
      console.log('Fetching analytics URL:', url) // Debug log
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      
      console.log('Analytics response status:', response.status) // Debug log
      
      if (response.ok) {
        const data = await response.json()
        console.log('Analytics data received:', data) // Debug log
        setAnalytics(data)
      } else {
        const errorText = await response.text()
        console.error('Analytics API Error:', response.status, errorText)
        setError(`Failed to load analytics: ${response.status} - ${errorText}`)
      }
    } catch (error) {
      console.error('Failed to load analytics:', error)
      setError('Failed to load analytics: ' + error.message)
    }
  }

  const searchEmails = async () => {
    if (!searchQuery.trim()) return
    
    setIsLoading(true)
    try {
      const response = await fetch(`${BASE_URL}/api/emails/search?user_id=${USER_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, limit: 10 })
      })
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data)
      }
    } catch (error) {
      console.error('Search failed:', error)
    }
    setIsLoading(false)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high': return '#ff4757'
      case 'medium': return '#ffa502'
      case 'low': return '#2ed573'
      default: return '#747d8c'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category?.toLowerCase()) {
      case 'work': return '#3742fa'
      case 'personal': return '#2f3542'
      case 'promotional': return '#ff6348'
      default: return '#747d8c'
    }
  }

  const getSentimentEmoji = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return '😊'
      case 'negative': return '😟'
      case 'neutral': return '😐'
      default: return '❓'
    }
  }

  return (
    <div className="email-dashboard">
      <div className="dashboard-header">
        <h1>📧 Email Dashboard</h1>
        {error && (
          <div style={{ color: '#ff4757', padding: '10px', background: '#2d2d2d', borderRadius: '5px', marginBottom: '20px' }}>
            Error: {error}
          </div>
        )}
        <div className="tab-navigation">
          <button 
            className={activeTab === 'emails' ? 'active' : ''}
            onClick={() => setActiveTab('emails')}
          >
            📧 Emails ({emails.length})
          </button>
          <button 
            className={activeTab === 'search' ? 'active' : ''}
            onClick={() => setActiveTab('search')}
          >
            🔍 Search
          </button>
          <button 
            className={activeTab === 'analytics' ? 'active' : ''}
            onClick={() => setActiveTab('analytics')}
          >
            📊 Analytics
          </button>
          <button 
            className={activeTab === 'sync' ? 'active' : ''}
            onClick={() => setActiveTab('sync')}
          >
            🔄 Gmail Sync
          </button>
        </div>
      </div>

      {/* Debug info */}
      <div style={{ background: '#20232a', padding: '10px', borderRadius: '5px', marginBottom: '20px', fontSize: '14px' }}>
        <p>USER_ID: {USER_ID}</p>
        <p>Backend URL: {BASE_URL}</p>
        <p>Emails loaded: {emails.length}</p>
        <p>Active tab: {activeTab}</p>
      </div>

      {activeTab === 'emails' && (
        <div className="emails-tab">
          <h2>Recent Emails</h2>
          {emails.length > 0 ? (
            <div className="emails-list">
              {emails.map((email) => (
                <div key={email.id} className="email-card">
                  <h3 className="email-subject">{email.subject}</h3>
                  <p><strong>From:</strong> {email.sender}</p>
                  <p className="email-summary">{email.summary}</p>
                  <p><strong>Category:</strong> {email.category} | <strong>Priority:</strong> {email.priority}</p>
                </div>
              ))}
            </div>
          ) : (
            <p>No emails found. Check if backend is running and test data is loaded.</p>
          )}
        </div>
      )}

      {activeTab === 'search' && (
        <div className="search-tab">
          <h2>🔍 Search Emails</h2>
          <p>Search functionality will be here</p>
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="analytics-tab">
          <h2>📊 Analytics</h2>
          {analytics ? (
            <pre>{JSON.stringify(analytics, null, 2)}</pre>
          ) : (
            <p>No analytics data available</p>
          )}
        </div>
      )}

      {/* Add Gmail Sync tab */}
      {activeTab === 'sync' && (
        <div className="sync-tab">
          <GmailSync userId={USER_ID} />
        </div>
      )}
    </div>
  )
}

export default EmailDashboard