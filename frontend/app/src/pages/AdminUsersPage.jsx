import { useCallback, useEffect, useState } from 'react'
import { adminUsersApi } from '../api/client.js'
import { AdminShell } from '../components/AdminShell.jsx'
import { AdminUserPasswordDialog } from '../components/AdminUserPasswordDialog.jsx'
import '../styles/dialog.css'

const registeredAtFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function formatRegisteredAt(value) {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : registeredAtFormatter.format(date)
}

export default function AdminUsersPage() {
  const [items, setItems] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [passwordUser, setPasswordUser] = useState(null)
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    setState('loading')
    try {
      setItems(await adminUsersApi.list())
      setError('')
      setState('ready')
    } catch (loadError) {
      setError(loadError.message)
      setState('error')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!toast) {
      return undefined
    }
    const timer = window.setTimeout(() => setToast(''), 2400)
    return () => window.clearTimeout(timer)
  }, [toast])

  return (
    <AdminShell title="Управление пользователями" toast={toast}>
      {state === 'loading' && <p className="pantry__message">Загружаем пользователей...</p>}

      {state === 'error' && (
        <div className="pantry__message">
          <p>{error}</p>
          <button className="btn btn--ghost" type="button" onClick={load}>
            Повторить
          </button>
        </div>
      )}

      {state === 'ready' && items.length === 0 && (
        <p className="pantry__message">Пользователей пока нет</p>
      )}

      {state === 'ready' && items.length > 0 && (
        <ul className="news__list admin-users__list">
          {items.map((item) => (
            <li className="admin-users__item" key={item.id}>
              <div className="admin-users__main">
                <span className="admin-users__login">{item.login}</span>
                <time
                  className="admin-users__time"
                  dateTime={item.datetime_registered ?? undefined}
                >
                  {formatRegisteredAt(item.datetime_registered)}
                </time>
              </div>
              <button
                className="btn btn--ghost admin-users__password-btn"
                type="button"
                onClick={() => setPasswordUser(item)}
              >
                Сменить пароль
              </button>
            </li>
          ))}
        </ul>
      )}

      {passwordUser != null && (
        <AdminUserPasswordDialog
          user={passwordUser}
          onClose={() => setPasswordUser(null)}
          onSaved={() => setToast('Пароль изменён')}
        />
      )}
    </AdminShell>
  )
}
