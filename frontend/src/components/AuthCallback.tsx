import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('Processing...')

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get the current URL (which should have been set by the backend callback)
        const response = await fetch(window.location.href.replace(window.location.origin, 'http://localhost:8000'))
        
        if (response.ok) {
          const data = await response.json()
          // Store user ID for future requests
          localStorage.setItem('userId', data.user.user_id)
          setStatus('Login successful! Redirecting...')
          
          // Redirect to main app after a short delay
          setTimeout(() => {
            window.location.href = '/'
          }, 2000)
        } else {
          setStatus('Login failed. Please try again.')
        }
      } catch (error) {
        console.error('Auth callback error:', error)
        setStatus('Login failed. Please try again.')
      }
    }

    handleCallback()
  }, [])

  return (
    <div className="auth-callback">
      <h2>{status}</h2>
    </div>
  )
}