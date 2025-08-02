import { useState, useEffect } from 'react'
import Calendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import './CalendarCustom.css'

interface Event {
  id: number
  title: string
  description?: string
  datetime: string // ISO string with time
}

export default function SimpleCalendar() {
  const [date, setDate] = useState<Date | [Date, Date]>(new Date())
  const [events, setEvents] = useState<Event[]>([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [time, setTime] = useState('12:00')
  const [editingEvent, setEditingEvent] = useState<Event | null>(null)
  const [dayViewDate, setDayViewDate] = useState<Date | null>(null)

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

  // Handle event creation or editing
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    // Use dayViewDate if set, otherwise use date
    const eventDate = dayViewDate ? dayViewDate : (Array.isArray(date) ? date[0] : date)
    const [hours, minutes] = time.split(':').map(Number)
    const eventDateTime = new Date(eventDate)
    eventDateTime.setHours(hours, minutes, 0, 0)
    const payload = {
      title,
      description,
      datetime: eventDateTime.toISOString(),
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

  // Start editing an event
  function startEdit(ev: Event) {
    setEditingEvent(ev)
    setTitle(ev.title)
    setDescription(ev.description || '')
    setTime(new Date(ev.datetime).toTimeString().slice(0, 5))
    setDate(new Date(ev.datetime))
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

  return (
    <div>
      <h2>Calendar</h2>
      <div style={{ maxWidth: 350, margin: '0 auto' }}>
        <Calendar
          onChange={setDate}
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
      <ul>
        {selectedEvents.map(ev => (
          <li key={ev.id}>
            <strong>{ev.title}</strong>
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
      <form onSubmit={handleSubmit} style={{ marginTop: 16 }}>
        <h3>{editingEvent ? 'Edit Event' : 'Add Event'}</h3>
        <input
          type="text"
          placeholder="Title"
          value={title}
          required
          onChange={e => setTitle(e.target.value)}
        />
        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        <input
          type="time"
          value={time}
          required
          onChange={e => setTime(e.target.value)}
        />
        <button type="submit">{editingEvent ? 'Update' : 'Add'}</button>
        {editingEvent && (
          <button type="button" onClick={cancelEdit} style={{ marginLeft: 8 }}>
            Cancel
          </button>
        )}
      </form>
      {dayViewDate && (
        <div style={{ maxHeight: 400, overflowY: 'auto', border: '1px solid #e5e7eb', marginTop: 16, padding: 8 }}>
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
              return (
                <li key={hour} style={{ borderBottom: '1px solid #e5e7eb', padding: '4px 0' }}>
                  <strong>{blockTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
                  {blockEvents.length > 0 ? (
                    blockEvents.map(ev => (
                      <div key={ev.id}>
                        <span>{ev.title}</span>
                        {ev.description && <>: {ev.description}</>}
                      </div>
                    ))
                  ) : (
                    <span style={{ color: '#cbd5e1', marginLeft: 8 }}>No events</span>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}