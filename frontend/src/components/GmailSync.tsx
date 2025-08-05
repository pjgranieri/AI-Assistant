import React, { useState, useEffect } from 'react'

interface GmailSyncProps {
  userId?: string
}

export default function GmailSync({ userId }: GmailSyncProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [syncStatus, setSyncStatus] = useState<string>('')
  const [lastSync, setLastSync] = useState<string>('')

  const BASE_URL = 'http://localhost:8000'

  useEffect(() => {
    if (userId) {
      checkGmailStatus()
    }
  }, [userId])

  const checkGmailStatus = async () => {
    if (!userId) return

    try {
      const response = await fetch(`${BASE_URL}/api/gmail/status?user_id=${userId}`)
      const data = await response.json()
      setIsConnected(data.connected)
      setSyncStatus(data.message)
    } catch (error) {
      console.error('Failed to check Gmail status:', error)
      setSyncStatus('Failed to check Gmail connection')
    }
  }

  const handleGmailSync = async (days: number = 7) => {
    if (!userId) {
      setSyncStatus('Please log in first')
      return
    }

    setIsLoading(true)
    setSyncStatus('Syncing emails...')

    try {
      const response = await fetch(`${BASE_URL}/api/gmail/sync?user_id=${userId}&days=${days}`, {
        method: 'POST'
      })

      if (response.ok) {
        const result = await response.json()
        setSyncStatus(`Sync completed! Processed ${result.processed_count} new emails, skipped ${result.skipped_count} existing ones.`)
        setLastSync(new Date().toLocaleString())
        
        // Trigger a refresh of the email dashboard
        window.dispatchEvent(new CustomEvent('emailsUpdated'))
      } else {
        const error = await response.text()
        setSyncStatus(`Sync failed: ${error}`)
      }
    } catch (error) {
      console.error('Gmail sync failed:', error)
      setSyncStatus('Sync failed: Connection error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleConnectGmail = () => {
    // Redirect to Gmail OAuth
    window.location.href = `${BASE_URL}/auth/google`
  }

  return (
    <div className="gmail-sync-section">
      <h3>📧 Gmail Integration</h3>
      
      <div className="connection-status">
        <p>
          Status: {isConnected ? (
            <span style={{ color: '#2ed573' }}>✅ Connected</span>
          ) : (
            <span style={{ color: '#ff4757' }}>❌ Not Connected</span>
          )}
        </p>
        <p style={{ fontSize: '0.9em', color: '#ccc' }}>{syncStatus}</p>
        {lastSync && (
          <p style={{ fontSize: '0.8em', color: '#999' }}>
            Last sync: {lastSync}
          </p>
        )}
      </div>

      <div className="sync-controls">
        {!isConnected ? (
          <button 
            onClick={handleConnectGmail}
            className="connect-gmail-btn"
            style={{
              background: '#4285f4',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              marginBottom: '10px',
              width: '100%'
            }}
          >
            🔗 Connect Gmail
          </button>
        ) : (
          <div className="sync-options">
            <button 
              onClick={() => handleGmailSync(1)}
              disabled={isLoading}
              style={{
                background: '#27ae60',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                margin: '5px',
                opacity: isLoading ? 0.6 : 1
              }}
            >
              Sync Last 24h
            </button>
            <button 
              onClick={() => handleGmailSync(7)}
              disabled={isLoading}
              style={{
                background: '#27ae60',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                margin: '5px',
                opacity: isLoading ? 0.6 : 1
              }}
            >
              Sync Last Week
            </button>
            <button 
              onClick={() => handleGmailSync(30)}
              disabled={isLoading}
              style={{
                background: '#f39c12',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                margin: '5px',
                opacity: isLoading ? 0.6 : 1
              }}
            >
              Sync Last Month
            </button>
          </div>
        )}
      </div>

      {isLoading && (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <div style={{ 
            width: '20px', 
            height: '20px', 
            border: '2px solid #f3f3f3',
            borderTop: '2px solid #3498db',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto'
          }}></div>
          <p style={{ marginTop: '10px', fontSize: '14px' }}>Processing emails...</p>
        </div>
      )}
    </div>
  )
}