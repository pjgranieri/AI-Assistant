import { useEffect, useState } from 'react'
import { supabase } from '../services/supabaseClient'

export default function Account() {
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user))
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })
    return () => listener?.subscription.unsubscribe()
  }, [])

  if (!user) return null

  return (
    <div>
      <p>Signed in as {user.email}</p>
      <button onClick={() => supabase.auth.signOut()}>Sign Out</button>
    </div>
  )
}