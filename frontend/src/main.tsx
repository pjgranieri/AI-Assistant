import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.tsx'
import AuthCallback from './components/AuthCallback.tsx'
import SimpleCalendar from './components/Calendar.tsx'
import EmailDashboard from './components/EmailDashboard.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<SimpleCalendar />} />
          <Route path="emails" element={<EmailDashboard />} />
        </Route>
        <Route path="/auth/google/callback" element={<AuthCallback />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
