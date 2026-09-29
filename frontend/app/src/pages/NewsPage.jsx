import { useEffect, useState } from 'react'
import { newsApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { formatRuDate } from '../lib/pantry.js'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/settings.css'
import '../styles/feedback.css'

function when(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const iso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  return formatRuDate(iso)
}

export default function NewsPage() {
  const { user, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [toast, setToast] = useToast()

  useEffect(() => {
    let cancelled = false
    newsApi
      .markRead(user.id)
      .catch(() => {})
      .then(() => newsApi.list())
      .then((rows) => {
        if (!cancelled) {
          setItems(rows)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
        }
      })

    return () => {
      cancelled = true
    }
  }, [user.id])

  return (
    <div className={`pantry pantry--settings${menuOpen ? ' pantry--menu-open' : ''}`}>
      <div className="pantry__app">
        <AppHeader
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((open) => !open)}
          onBell={() => setToast('Уведомления появятся позже')}
          onToast={setToast}
        />

        <main className="content">
          <h1 className="settings__title">Новости</h1>
          {error && <p className="settings-profile__meta">{error}</p>}
          {!error && items.length === 0 && <p className="settings-profile__meta">Новостей пока нет.</p>}
          {items.map((item) => (
            <article className="admin-mail" key={item.id}>
              <p className="admin-mail__when">{when(item.date_time)}</p>
              <p className="admin-mail__who">{item.title}</p>
              <p className="admin-mail__text">{item.body}</p>
            </article>
          ))}
        </main>
      </div>

      <PantryDock open={menuOpen} onClose={() => setMenuOpen(false)} onSignOut={signOut} />
      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
