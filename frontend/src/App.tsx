import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import './App.css'
import SignIn from './components/SignIn'
import Account from './components/Account'
import { supabase } from './services/supabaseClient'

function Home() {
  const [user, setUser] = useState<any>(null)
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user))
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })
    return () => listener?.subscription.unsubscribe()
  }, [])
  return (
    <>
      <h1>Home Page</h1>
      {user ? <Account /> : <SignIn />}
    </>
  )
}

function About() {
  return <h1>About Page</h1>
}

function App() {
  return (
    <BrowserRouter>
      <nav>
        <Link to="/">Home</Link> | <Link to="/about">About</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
