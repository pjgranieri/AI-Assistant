import React, { useState, useEffect } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'  // Remove Routes, Route, add Outlet
import './App.css'

function App() {
  const [user, setUser] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const location = useLocation()

  useEffect(() => {
    // Check for user info in URL params (from OAuth redirect)
    const urlParams = new URLSearchParams(location.search)
    const userId = urlParams.get('user_id')
    const email = urlParams.get('email')
    
    if (userId && email) {
      const userData = { id: userId, email: email }
      setUser(userData)
      localStorage.setItem('user', JSON.stringify(userData))
      
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
    } else {
      // Check localStorage for existing user
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        setUser(JSON.parse(savedUser))
      }
    }
    
    setIsLoading(false)
  }, [location.search])

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('user')
  }

  if (isLoading) {
    return <div className="loading">Loading...</div>
  }

  return (
    <div className="App">
      <header className="App-header">
        <nav className="nav-container">
          {/* Left side - AI Assistant title */}
          <div className="nav-left">
            <h1 className="app-title">AI Assistant</h1>
          </div>
          
          {/* Center - Navigation links */}
          <div className="nav-center">
            <Link to="/" className="nav-link">📅 Calendar</Link>
            <Link to="/emails" className="nav-link">📧 Emails</Link>
          </div>
          
          {/* Right side - User info */}
          <div className="nav-right">
            {user ? (
              <div className="user-info">
                <span className="user-email">👤 {user.email}</span>
                <button onClick={handleLogout} className="logout-btn">Logout</button>
              </div>
            ) : (
              <a href="http://localhost:8000/auth/google" className="login-btn">
                🔐 Login with Google
              </a>
            )}
          </div>
        </nav>
      </header>

      <main className="main-content">
        <Outlet />  {/* This replaces the Routes/Route structure */}
      </main>
    </div>
  )
}

export default App
