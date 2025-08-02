import { useState } from 'react'
import Calendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import './CalendarCustom.css'

export default function SimpleCalendar() {
  const [date, setDate] = useState<Date | [Date, Date]>(new Date())

  return (
    <div>
      <h2>Calendar</h2>
      <Calendar onChange={(value) => setDate(value as Date | [Date, Date])} value={date} />
      <p>Selected date: {Array.isArray(date) ? date.map(d => d.toDateString()).join(', ') : date.toDateString()}</p>
    </div>
  )
}