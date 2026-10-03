import { PantryDock } from './PantryDock.jsx'
import { AdminHeader } from './AdminHeader.jsx'
import { FeedbackIcon, NewsIcon } from './icons.jsx'
import '../styles/pantry.css'
import '../styles/settings.css'
import '../styles/admin.css'

const ADMIN_TABS = [
  { key: 'admin-news', title: 'Управление новостями', icon: <NewsIcon />, path: '/admin/news' },
  { key: 'admin-feedback', title: 'Обратная связь', icon: <FeedbackIcon />, path: '/admin/feedback' },
]

export function AdminShell({ title, children, toast, onAdd }) {
  return (
    <div className="pantry pantry--admin">
      <div className="pantry__app">
        <AdminHeader />

        <main className="content">
          <h1 className="settings__title">{title}</h1>
          {children}
        </main>
      </div>

      <PantryDock tabs={ADMIN_TABS} onAdd={onAdd} addLabel="Добавить новость" />

      {toast !== undefined && (
        <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
          {toast}
        </div>
      )}
    </div>
  )
}
