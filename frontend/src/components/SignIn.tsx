import React, { useState } from 'react'
import { supabase } from '../services/supabaseClient'

export default function SignIn() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    const { error } = await supabase.auth.signInWithOtp({ email })
    setMessage(error ? error.message : 'Check your email for the login link!')
  }

  return (
    <form onSubmit={handleSignIn}>
      <input
        type="email"
        placeholder="Your email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        required
      />
      <button type="submit">Sign In</button>
      {message && <div>{message}</div>}
    </form>
  )
}