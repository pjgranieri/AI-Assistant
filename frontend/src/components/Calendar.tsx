import { useState, useEffect } from 'react'
import Calendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import './CalendarCustom.css'
import CalendarSettings from './CalendarSettings'

interface Event {
  id: number
  title: string
  description?: string
  datetime: string // ISO string with time
}

interface CalendarSettingsType {
  timezone: string
  use24h: boolean
}

export default function SimpleCalendar() {
  const [date, setDate] = useState<Date | [Date, Date]>(new Date())
  const [events, setEvents] = useState<Event[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [time, setTime] = useState('12:00')
  const [editingEvent, setEditingEvent] = useState<Event | null>(null)
  const [dayViewDate, setDayViewDate] = useState<Date | null>(null)
  const [calendarSettings, setCalendarSettings] = useState<CalendarSettingsType>({
    timezone: 'US/Eastern',
    use24h: false
  })

  // Fetch events from backend
  useEffect(() => {
    fetchEvents()
  }, [])

  async function fetchEvents() {
    const res = await fetch('http://localhost:8000/events')
    const data = await res.json()
    setEvents(data)
  }

  // Helper: check if a date has an event
  function hasEvent(date: Date) {
    return events.some(ev => {
      const evDate = new Date(ev.datetime)
      return (
        evDate.getFullYear() === date.getFullYear() &&
        evDate.getMonth() === date.getMonth() &&
        evDate.getDate() === date.getDate()
      )
    })
  }

  // Custom tile content to show a dot for event days
  function tileContent({ date, view }: { date: Date; view: string }) {
    if (view === 'month' && hasEvent(date)) {
      return <span style={{ color: '#2563eb', fontWeight: 'bold' }}>•</span>
    }
    return null
  }

  // Show events for selected date
  const selectedEvents = Array.isArray(date)
    ? []
    : events.filter(ev => {
        const evDate = new Date(ev.datetime)
        return (
          evDate.getFullYear() === date.getFullYear() &&
          evDate.getMonth() === date.getMonth() &&
          evDate.getDate() === date.getDate()
        )
      })

  // FIXED: Handle event creation - keep time in local timezone
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    
    // Use dayViewDate if set, otherwise use date
    const eventDate = dayViewDate ? dayViewDate : (Array.isArray(date) ? date[0] : date)
    
    // Parse the time input (HH:MM format)
    const [hours, minutes] = time.split(':').map(Number)
    
    // Create the datetime string in the format the backend expects
    // Format: YYYY-MM-DDTHH:mm:ss (without timezone conversion)
    const year = eventDate.getFullYear()
    const month = String(eventDate.getMonth() + 1).padStart(2, '0')
    const day = String(eventDate.getDate()).padStart(2, '0')
    const hourStr = String(hours).padStart(2, '0')
    const minuteStr = String(minutes).padStart(2, '0')
    
    // Create ISO string but treat it as local time (no UTC conversion)
    const localDateTimeString = `${year}-${month}-${day}T${hourStr}:${minuteStr}:00`
    
    console.log('Selected date:', eventDate.toDateString())
    console.log('Selected time:', time)
    console.log('Local datetime string being sent:', localDateTimeString)
    
    const payload = {
      title,
      description,
      datetime: localDateTimeString, // Send as local time string
    }
    
    if (editingEvent) {
      // Edit event
      const res = await fetch(`http://localhost:8000/events/${editingEvent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        fetchEvents()
        setEditingEvent(null)
      }
    } else {
      // Create event
      const res = await fetch('http://localhost:8000/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const newEvent = await res.json()
        setEvents(events => [...events, newEvent])
      }
    }
    setTitle('')
    setDescription('')
    setTime('12:00')
  }

  // FIXED: Start editing an event - extract local time properly
  function startEdit(ev: Event) {
    setEditingEvent(ev)
    setTitle(ev.title)
    setDescription(ev.description || '')
    
    // Parse the datetime string directly (don't convert to Date object)
    const datetimeStr = ev.datetime
    let timeString = '12:00'
    
    if (datetimeStr.includes('T')) {
      // Extract time portion from ISO string
      const timePart = datetimeStr.split('T')[1]
      if (timePart) {
        timeString = timePart.substring(0, 5) // Get HH:mm part
      }
    } else {
      // Fallback: convert to date and extract time
      const eventDate = new Date(ev.datetime)
      timeString = eventDate.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    }
    
    setTime(timeString)
    
    // Set the date for the calendar
    const eventDate = new Date(ev.datetime)
    setDate(eventDate)
    
    console.log('Editing event:', ev.title)
    console.log('Original datetime:', ev.datetime)
    console.log('Extracted time:', timeString)
  }

  // Cancel editing
  function cancelEdit() {
    setEditingEvent(null)
    setTitle('')
    setDescription('')
    setTime('12:00')
  }

  function handleDayClick(value: Date) {
    if (window.confirm(`View full day for ${value.toDateString()}?`)) {
      setDayViewDate(value)
    }
  }

  // Helper function to format event time for display based on settings
  function formatEventTime(datetimeString: string) {
    const eventDate = new Date(datetimeString)
    return eventDate.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: !calendarSettings.use24h 
    })
  }

  // Handle settings changes
  function handleSettingsChange(newSettings: CalendarSettingsType) {
    setCalendarSettings(newSettings)
    console.log('Settings updated:', newSettings)
  }

  return (
    <div className="calendar-container">
      <div className="calendar-section">
        <h2>Calendar</h2>
        <div style={{ maxWidth: 350, margin: '0 auto' }}>
          <Calendar
            onChange={(value: Date | Date[] | null, event: React.MouseEvent<HTMLButtonElement>) => {
              if (Array.isArray(value)) {
                setDate([value[0], value[1]] as [Date, Date])
              } else {
                if (value) {
                  setDate(value)
                }
              }
            }}
            value={date}
            tileContent={tileContent}
            onClickDay={handleDayClick}
          />
        </div>
        <p>
          Selected date:{' '}
          {Array.isArray(date)
            ? date.map(d => d.toDateString()).join(', ')
            : (date as Date).toDateString()}
        </p>
        <p style={{ fontSize: '0.9rem', color: '#ccc' }}>
          Timezone: {calendarSettings.timezone} | 
          Format: {calendarSettings.use24h ? '24-hour' : '12-hour'}
        </p>
        <ul>
          {selectedEvents.map(ev => (
            <li key={ev.id}>
              <strong>{ev.title}</strong> at {formatEventTime(ev.datetime)}
              {ev.description && <>: {ev.description}</>}
              <button style={{ marginLeft: 8 }} onClick={() => startEdit(ev)}>
                Edit
              </button>
              <button
                style={{ marginLeft: 8, color: 'red' }}
                onClick={async () => {
                  await fetch(`http://localhost:8000/events/${ev.id}`, { method: 'DELETE' })
                  fetchEvents()
                }}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
      
      <div className="events-section">
        <CalendarSettings onSettingsChange={handleSettingsChange} />
        <div className="add-event-section">
          <form onSubmit={handleSubmit} style={{ marginTop: 16 }}>
            <h3>{editingEvent ? 'Edit Event' : 'Add Event'}</h3>
            <input
              type="text"
              placeholder="Title"
              value={title}
              required
              onChange={e => setTitle(e.target.value)}
              style={{ marginBottom: '0.5rem', padding: '0.5rem', width: '100%' }}
            />
            <input
              type="text"
              placeholder="Description"
              value={description}
              onChange={e => setDescription(e.target.value)}
              style={{ marginBottom: '0.5rem', padding: '0.5rem', width: '100%' }}
            />
            <input
              type="time"
              value={time}
              required
              onChange={e => setTime(e.target.value)}
              style={{ marginBottom: '0.5rem', padding: '0.5rem', width: '100%' }}
            />
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
              <button type="submit" style={{ padding: '0.5rem 1rem' }}>
                {editingEvent ? 'Update' : 'Add'}
              </button>
              {editingEvent && (
                <button type="button" onClick={cancelEdit} style={{ padding: '0.5rem 1rem' }}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>
        
        <div className="daily-events-section">
          {dayViewDate && (
            <div style={{ maxHeight: 400, overflowY: 'auto', border: '1px solid #404040', marginTop: 16, padding: 8 }}>
              <h3>
                Events for {dayViewDate.toDateString()}
                <button style={{ marginLeft: 8 }} onClick={() => setDayViewDate(null)}>Close</button>
              </h3>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {Array.from({ length: 24 }).map((_, hour) => {
                  const blockTime = new Date(dayViewDate)
                  blockTime.setHours(hour, 0, 0, 0)
                  const blockEvents = events.filter(ev => {
                    const evDate = new Date(ev.datetime)
                    return (
                      evDate.getFullYear() === dayViewDate.getFullYear() &&
                      evDate.getMonth() === dayViewDate.getMonth() &&
                      evDate.getDate() === dayViewDate.getDate() &&
                      evDate.getHours() === hour
                    )
                  })
                  
                  const timeFormat = calendarSettings.use24h 
                    ? { hour: '2-digit', minute: '2-digit', hour12: false }
                    : { hour: '2-digit', minute: '2-digit', hour12: true }
                  
                  return (
                    <li key={hour} style={{ borderBottom: '1px solid #404040', padding: '4px 0' }}>
                      <strong>{blockTime.toLocaleTimeString([], timeFormat as any)}</strong>
                      {blockEvents.length > 0 ? (
                        blockEvents.map(ev => (
                          <div key={ev.id} style={{ marginLeft: '1rem', color: '#e0e0e0' }}>
                            <span>{ev.title}</span>
                            {ev.description && <>: {ev.description}</>}
                          </div>
                        ))
                      ) : (
                        <span style={{ color: '#666', marginLeft: 8 }}>No events</span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}