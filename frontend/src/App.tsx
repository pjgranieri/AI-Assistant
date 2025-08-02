import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import './App.css'
import SimpleCalendar from './components/Calendar'

function App() {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const location = useLocation()

  // Check if user is logged in on app load
  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = async () => {
    try {
      // Check URL parameters first (from OAuth callback)
      const urlParams = new URLSearchParams(window.location.search)
      const userIdFromUrl = urlParams.get('user_id')
      const emailFromUrl = urlParams.get('email')
      
      if (userIdFromUrl && emailFromUrl) {
        // Store user data from OAuth callback
        localStorage.setItem('userId', userIdFromUrl)
        const userData = { user_id: userIdFromUrl, email: emailFromUrl }
        setUser(userData)
        
        // Clean up URL
        window.history.replaceState({}, document.title, '/')
        return
      }

      // Check if user ID exists in localStorage
      const userId = localStorage.getItem('userId')
      if (userId) {
        const response = await fetch(`http://localhost:8000/auth/user/${userId}`)
        if (response.ok) {
          const userData = await response.json()
          setUser(userData)
        } else {
          localStorage.removeItem('userId')
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('userId')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleLogin = () => {
    // Redirect to Google OAuth
    window.location.href = 'http://localhost:8000/auth/google'
  }

  const handleLogout = async () => {
    try {
      const userId = localStorage.getItem('userId')
      if (userId) {
        await fetch(`http://localhost:8000/auth/logout/${userId}`, {
          method: 'DELETE'
        })
      }
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      localStorage.removeItem('userId')
      setUser(null)
    }
  }

  if (isLoading) {
    return <div className="loading">Loading...</div>
  }

  // Show login screen if not authenticated
  if (!user) {
    return (
      <div className="login-container">
        <h1>AI Assistant</h1>
        <p>Please sign in with Google to access your calendar and emails</p>
        <button onClick={handleGoogleLogin} className="google-login-btn">
          Sign in with Google
        </button>
      </div>
    )
  }

  // Show main app if authenticated
  return (
    <div className="App">
      <header className="app-header">
        <h1>AI Assistant</h1>
        <div className="user-info">
          <span>Welcome, {user.email}</span>
          <button onClick={handleLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </header>
      
      <div className="nav-bar">
        <nav>
          <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
            Calendar
          </Link>
          <Link to="/about" className={location.pathname === '/about' ? 'active' : ''}>
            About
          </Link>
        </nav>
      </div>
      
      <main>
        <div className="calendar-container">
          <Routes>
            <Route path="/" element={<SimpleCalendar />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function About() {
  return (
    <div className="about-container">
      <h1>About AI Assistant</h1>
      <p>Your personal AI-powered calendar and email assistant powered by Google OAuth and advanced AI capabilities.</p>
    </div>
  )
}

export default App
