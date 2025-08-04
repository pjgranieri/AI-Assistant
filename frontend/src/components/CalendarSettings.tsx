import React, { useState, useEffect } from 'react'

interface Timezone {
  value: string
  label: string
}

interface CalendarSettingsProps {
  onSettingsChange: (settings: { timezone: string; use24h: boolean }) => void
}

export default function CalendarSettings({ onSettingsChange }: CalendarSettingsProps) {
  const [timezone, setTimezone] = useState('US/Eastern')
  const [use24h, setUse24h] = useState(false)
  const [timezones, setTimezones] = useState<Timezone[]>([])
  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    // Load settings from localStorage
    const savedTimezone = localStorage.getItem('calendar_timezone') || 'US/Eastern'
    const saved24h = localStorage.getItem('calendar_24h') === 'true'
    
    setTimezone(savedTimezone)
    setUse24h(saved24h)
    
    // Fetch available timezones
    fetchTimezones()
    
    // Notify parent of current settings
    onSettingsChange({ timezone: savedTimezone, use24h: saved24h })
  }, [])

  const fetchTimezones = async () => {
    try {
      const response = await fetch('http://localhost:8000/timezones')
      if (response.ok) {
        const data = await response.json()
        setTimezones(data)
      }
    } catch (error) {
      console.error('Failed to fetch timezones:', error)
    }
  }

  const handleTimezoneChange = (newTimezone: string) => {
    setTimezone(newTimezone)
    localStorage.setItem('calendar_timezone', newTimezone)
    onSettingsChange({ timezone: newTimezone, use24h })
  }

  const handle24hChange = (new24h: boolean) => {
    setUse24h(new24h)
    localStorage.setItem('calendar_24h', new24h.toString())
    onSettingsChange({ timezone, use24h: new24h })
  }

  const clearCalendar = async () => {
    if (window.confirm('Are you sure you want to clear ALL events? This cannot be undone.')) {
      try {
        const response = await fetch('http://localhost:8000/events', {
          method: 'DELETE'
        })
        if (response.ok) {
          alert('Calendar cleared successfully!')
          // Refresh the page to update the calendar
          window.location.reload()
        } else {
          alert('Failed to clear calendar')
        }
      } catch (error) {
        console.error('Error clearing calendar:', error)
        alert('Error clearing calendar')
      }
    }
  }

  return (
    <div className="calendar-settings-section">
      <button 
        className="settings-toggle-btn"
        onClick={() => setShowSettings(!showSettings)}
      >
        ⚙️ Settings
      </button>
      
      {showSettings && (
        <div className="settings-panel">
          <h3>Calendar Settings</h3>
          
          <div className="setting-group">
            <label>Timezone:</label>
            <select 
              value={timezone} 
              onChange={(e) => handleTimezoneChange(e.target.value)}
              className="timezone-select"
            >
              {timezones.map(tz => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
          </div>
          
          <div className="setting-group">
            <label>
              <input 
                type="checkbox" 
                checked={use24h}
                onChange={(e) => handle24hChange(e.target.checked)}
              />
              Use 24-hour format (Military Time)
            </label>
          </div>
          
          <div className="setting-group">
            <button 
              className="clear-calendar-btn"
              onClick={clearCalendar}
            >
              🗑️ Clear All Events
            </button>
          </div>
        </div>
      )}
    </div>
  )
}