import React, { useState, useEffect } from 'react'
import GmailSync from './GmailSync'  // Add this import
import CostMonitor from './CostMonitor'
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

type SortOption = 'date' | 'priority' | 'category'
type SortDirection = 'asc' | 'desc'

interface FilterState {
  category: string
  priority: string
  dateRange: {
    start: string
    end: string
  }
}

const EmailDashboard: React.FC = () => {
  console.log('EmailDashboard component rendering!') // Debug log
  
  const [emails, setEmails] = useState<Email[]>([])
  const [filteredEmails, setFilteredEmails] = useState<Email[]>([])
  const [sortedEmails, setSortedEmails] = useState<Email[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Email[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'emails' | 'search' | 'analytics' | 'sync'>('emails')
  const [error, setError] = useState<string | null>(null)
  const [isLoadingEmails, setIsLoadingEmails] = useState(true)
  
  // Sorting states
  const [sortBy, setSortBy] = useState<SortOption>('date')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  // Filter states
  const [filters, setFilters] = useState<FilterState>({
    category: '',
    priority: '',
    dateRange: {
      start: '',
      end: ''
    }
  })

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

  // Priority order for sorting
  const priorityOrder = { 'high': 3, 'medium': 2, 'low': 1 }

  // Get unique categories and priorities from emails
  const getUniqueCategories = () => {
    const categories = [...new Set(emails.map(email => email.category).filter(Boolean))]
    return categories.sort()
  }

  const getUniquePriorities = () => {
    const priorities = [...new Set(emails.map(email => email.priority).filter(Boolean))]
    return priorities.sort((a, b) => (priorityOrder[b.toLowerCase() as keyof typeof priorityOrder] || 0) - (priorityOrder[a.toLowerCase() as keyof typeof priorityOrder] || 0))
  }

  // Filter emails function
  const filterEmails = (emailsToFilter: Email[], filterState: FilterState): Email[] => {
    return emailsToFilter.filter(email => {
      // Category filter
      if (filterState.category && email.category !== filterState.category) {
        return false
      }

      // Priority filter
      if (filterState.priority && email.priority !== filterState.priority) {
        return false
      }

      // Date range filter
      if (filterState.dateRange.start || filterState.dateRange.end) {
        const emailDate = new Date(email.received_at)
        
        if (filterState.dateRange.start) {
          const startDate = new Date(filterState.dateRange.start)
          if (emailDate < startDate) return false
        }
        
        if (filterState.dateRange.end) {
          const endDate = new Date(filterState.dateRange.end)
          endDate.setHours(23, 59, 59, 999) // Include the entire end day
          if (emailDate > endDate) return false
        }
      }

      return true
    })
  }

  // Sort emails function
  const sortEmails = (emailsToSort: Email[], sortOption: SortOption, direction: SortDirection): Email[] => {
    const sorted = [...emailsToSort].sort((a, b) => {
      let aValue: any, bValue: any
      
      switch (sortOption) {
        case 'date':
          aValue = new Date(a.received_at).getTime()
          bValue = new Date(b.received_at).getTime()
          break
        case 'priority':
          aValue = priorityOrder[a.priority?.toLowerCase() as keyof typeof priorityOrder] || 0
          bValue = priorityOrder[b.priority?.toLowerCase() as keyof typeof priorityOrder] || 0
          break
        case 'category':
          aValue = a.category?.toLowerCase() || ''
          bValue = b.category?.toLowerCase() || ''
          break
        default:
          return 0
      }
      
      if (aValue < bValue) return direction === 'asc' ? -1 : 1
      if (aValue > bValue) return direction === 'asc' ? 1 : -1
      return 0
    })
    
    return sorted
  }

  // Update filtered and sorted emails when emails, filters, or sorting changes
  useEffect(() => {
    const filtered = filterEmails(emails, filters)
    setFilteredEmails(filtered)
    setSortedEmails(sortEmails(filtered, sortBy, sortDirection))
  }, [emails, filters, sortBy, sortDirection])

  const handleSortChange = (newSortBy: SortOption) => {
    if (sortBy === newSortBy) {
      // Toggle direction if same sort option
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // Set new sort option with default direction
      setSortBy(newSortBy)
      setSortDirection(newSortBy === 'date' ? 'desc' : 'asc')
    }
  }

  const handleFilterChange = (filterType: keyof FilterState, value: any) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value
    }))
  }

  const clearFilters = () => {
    setFilters({
      category: '',
      priority: '',
      dateRange: {
        start: '',
        end: ''
      }
    })
  }

  // Get date range for date picker (last 30 days max)
  const getDateLimits = () => {
    const today = new Date()
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(today.getDate() - 30)
    
    return {
      min: thirtyDaysAgo.toISOString().split('T')[0],
      max: today.toISOString().split('T')[0]
    }
  }

  useEffect(() => {
    console.log('EmailDashboard useEffect running...')
    const loadData = async () => {
      // First, load existing emails
      await loadEmails()
    }
    loadData()
  }, [])

  // Separate useEffect to handle test data after emails are loaded
  useEffect(() => {
    const addTestDataIfNeeded = async () => {
      // Only add test data if no emails exist and we've already tried to load emails
      if (emails.length === 0) {
        console.log('No emails found, adding test data...')
        await addTestData()
        await loadEmails() // Reload after adding test data
      } else {
        console.log(`Found ${emails.length} existing emails, skipping test data`)
      }
      
      // Load analytics after we have emails
      await loadAnalytics()
    }
    
    // Only run this after the first load attempt
    if (emails !== undefined) {
      addTestDataIfNeeded()
    }
  }, [emails.length]) // This will trigger when emails.length changes

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
      console.log('Checking if test data needed for user:', USER_ID)
      const response = await fetch(`${BASE_URL}/api/emails/test-data?user_id=${USER_ID}`, { 
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      const result = await response.json()
      console.log('Test data response:', result)
    } catch (error) {
      console.error('Failed to add test data:', error)
      setError('Failed to add test data: ' + error.message)
    }
  }

  const loadEmails = async () => {
    setIsLoadingEmails(true)
    try {
      console.log('Loading emails for user:', USER_ID)
      const response = await fetch(`${BASE_URL}/api/emails?user_id=${USER_ID}&limit=50`)
      if (response.ok) {
        const emailData = await response.json()
        console.log('Loaded emails:', emailData.length)
        setEmails(emailData)
      } else {
        console.error('Failed to load emails:', response.status)
        setError('Failed to load emails: ' + response.statusText)
      }
    } catch (error) {
      console.error('Error loading emails:', error)
      setError('Error loading emails: ' + error.message)
    } finally {
      setIsLoadingEmails(false)
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

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high': return '#e53e3e'
      case 'medium': return '#ed8936'
      case 'low': return '#48bb78'
      default: return '#718096'
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category.toLowerCase()) {
      case 'work': return '#3182ce'
      case 'personal': return '#805ad5'
      case 'promotional': return '#ed64a6'
      case 'financial': return '#38b2ac'
      case 'travel': return '#f56500'
      default: return '#718096'
    }
  }

  const getSentimentEmoji = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive': return '😊'
      case 'negative': return '😔'
      case 'neutral': return '😐'
      default: return '😐'
    }
  }

  const getSortIcon = (option: SortOption) => {
    if (sortBy !== option) return '↕️'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  const dateLimits = getDateLimits()

  // Add this function after your other helper functions (around line 280):
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
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
            📧 Emails ({sortedEmails.length}/{emails.length})
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

      {activeTab === 'emails' && (
        <div className="emails-tab">
          <div className="emails-header">
            <h2>Recent Emails</h2>
            <button className="refresh-btn" onClick={loadEmails}>
              🔄 Refresh
            </button>
          </div>

          {/* Combined Controls Section */}
          <div className="controls-section">
            <div className="controls-header">
              <h3>Filter & Sort</h3>
              <button className="clear-filters-btn" onClick={clearFilters}>
                Clear All
              </button>
            </div>
            
            <div className="controls-grid">
              {/* Sort Controls */}
              <div className="control-group">
                <label>Sort by:</label>
                <div className="sort-buttons">
                  <button 
                    className={`control-btn ${sortBy === 'date' ? 'active' : ''}`}
                    onClick={() => handleSortChange('date')}
                  >
                    Date {getSortIcon('date')}
                  </button>
                  <button 
                    className={`control-btn ${sortBy === 'priority' ? 'active' : ''}`}
                    onClick={() => handleSortChange('priority')}
                  >
                    Priority {getSortIcon('priority')}
                  </button>
                  <button 
                    className={`control-btn ${sortBy === 'category' ? 'active' : ''}`}
                    onClick={() => handleSortChange('category')}
                  >
                    Category {getSortIcon('category')}
                  </button>
                </div>
              </div>

              {/* Filter Controls */}
              <div className="control-group">
                <label>Filter by Category:</label>
                <select
                  value={filters.category}
                  onChange={(e) => handleFilterChange('category', e.target.value)}
                  className="control-select"
                >
                  <option value="">All Categories</option>
                  {getUniqueCategories().map(category => (
                    <option key={category} value={category}>
                      {category.charAt(0).toUpperCase() + category.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="control-group">
                <label>Filter by Priority:</label>
                <select
                  value={filters.priority}
                  onChange={(e) => handleFilterChange('priority', e.target.value)}
                  className="control-select"
                >
                  <option value="">All Priorities</option>
                  {getUniquePriorities().map(priority => (
                    <option key={priority} value={priority}>
                      {priority.charAt(0).toUpperCase() + priority.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="control-group">
                <label>Filter by Date Range:</label>
                <div className="date-range-controls">
                  <input
                    type="date"
                    value={filters.dateRange.start}
                    min={dateLimits.min}
                    max={dateLimits.max}
                    onChange={(e) => handleFilterChange('dateRange', {
                      ...filters.dateRange,
                      start: e.target.value
                    })}
                    className="control-date"
                    placeholder="Start date"
                  />
                  <span className="date-separator">to</span>
                  <input
                    type="date"
                    value={filters.dateRange.end}
                    min={filters.dateRange.start || dateLimits.min}
                    max={dateLimits.max}
                    onChange={(e) => handleFilterChange('dateRange', {
                      ...filters.dateRange,
                      end: e.target.value
                    })}
                    className="control-date"
                    placeholder="End date"
                  />
                </div>
              </div>
            </div>
          </div>

          {isLoadingEmails ? (
            <div className="loading-placeholder">
              Loading emails...
            </div>
          ) : sortedEmails.length > 0 ? (
            <div className="emails-list">
              {sortedEmails.map((email) => (
                <div key={email.id} className="email-card">
                  <div className="email-header">
                    <div className="email-meta">
                      <div className="email-sender">{email.sender}</div>
                      <div className="email-date">{formatDate(email.received_at)}</div>
                    </div>
                    <div className="email-badges">
                      <span 
                        className="priority-badge" 
                        style={{ backgroundColor: getPriorityColor(email.priority) }}
                      >
                        {email.priority}
                      </span>
                      <span 
                        className="category-badge"
                        style={{ backgroundColor: getCategoryColor(email.category) }}
                      >
                        {email.category}
                      </span>
                      <span className="sentiment-badge">
                        {getSentimentEmoji(email.sentiment)}
                      </span>
                    </div>
                  </div>
                  
                  <h3 className="email-subject">{email.subject}</h3>
                  <p className="email-summary">{email.summary}</p>
                  
                  {email.action_items && email.action_items !== 'None' && (
                    <div className="action-items">
                      <h4>📋 Action Items:</h4>
                      <pre>{email.action_items}</pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="no-results">
              <div>
                {emails.length === 0 ? (
                  <>
                    <h3>No emails found</h3>
                    <p>Check if backend is running and test data is loaded.</p>
                    <button 
                      className="refresh-btn" 
                      onClick={loadEmails}
                      style={{ marginTop: '16px' }}
                    >
                      🔄 Try Again
                    </button>
                  </>
                ) : (
                  <>
                    <h3>No emails match current filters</h3>
                    <p>Try adjusting your filters or search terms.</p>
                    <button 
                      className="clear-filters-btn" 
                      onClick={clearFilters}
                      style={{ marginTop: '16px' }}
                    >
                      Clear All Filters
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'search' && (
        <div className="search-tab">
          <div className="search-header">
            <h2>🔍 Search Emails</h2>
            <div className="search-box">
              <input
                type="text"
                placeholder="Search emails by content, subject, or sender..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchEmails()}
              />
              <button onClick={searchEmails} disabled={isLoading}>
                {isLoading ? '⏳' : '🔍'} Search
              </button>
            </div>
          </div>

          <div className="search-results">
            {searchResults.length > 0 ? (
              <div className="emails-list">
                {searchResults.map((email) => (
                  <div key={email.id} className="email-card">
                    <div className="email-header">
                      <div className="email-meta">
                        <div className="email-sender">{email.sender}</div>
                        <div className="email-date">{formatDate(email.received_at)}</div>
                      </div>
                      <div className="email-badges">
                        <span 
                          className="priority-badge" 
                          style={{ backgroundColor: getPriorityColor(email.priority) }}
                        >
                          {email.priority}
                        </span>
                        <span 
                          className="category-badge"
                          style={{ backgroundColor: getCategoryColor(email.category) }}
                        >
                          {email.category}
                        </span>
                        <span className="sentiment-badge">
                          {getSentimentEmoji(email.sentiment)}
                        </span>
                      </div>
                    </div>
                    
                    <h3 className="email-subject">{email.subject}</h3>
                    <p className="email-summary">{email.summary}</p>
                    
                    {email.action_items && email.action_items !== 'None' && (
                      <div className="action-items">
                        <h4>📋 Action Items:</h4>
                        <pre>{email.action_items}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : searchQuery ? (
              <div className="no-results">
                No emails found matching "{searchQuery}"
              </div>
            ) : (
              <div className="search-prompt">
                Enter a search term to find emails
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="analytics-tab">
          <h2>📊 Analytics</h2>
          
          {/* Add Cost Monitor */}
          <CostMonitor userId={USER_ID} />
          
          {analytics ? (
            <div className="analytics-grid">
              <div className="analytics-card">
                <h3>📊 Categories</h3>
                <div className="analytics-list">
                  {analytics.categories.map((cat, index) => (
                    <div key={index} className="analytics-item">
                      <span className="analytics-label">{cat.category}</span>
                      <span className="analytics-count">{cat.count}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="analytics-card">
                <h3>🔥 Priorities</h3>
                <div className="analytics-list">
                  {analytics.priorities.map((pri, index) => (
                    <div key={index} className="analytics-item">
                      <span className="analytics-label">{pri.priority}</span>
                      <span className="analytics-count">{pri.count}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="analytics-card">
                <h3>😊 Sentiments</h3>
                <div className="analytics-list">
                  {analytics.sentiments.map((sent, index) => (
                    <div key={index} className="analytics-item">
                      <span className="analytics-label">{sent.sentiment}</span>
                      <span className="analytics-count">{sent.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
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