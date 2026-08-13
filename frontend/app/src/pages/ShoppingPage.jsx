import { useState } from 'react'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import {
  BagIcon,
  CalendarIcon,
  CheckIcon,
  PlusIcon,
  ShareIcon,
  SparkIcon,
  TrashIcon,
} from '../components/icons.jsx'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/shopping.css'

export default function ShoppingPage() {
  const { signOut } = useAuth()

  const [items, setItems] = useState([])
  const [draft, setDraft] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useToast()

  function addItem(event) {
    event.preventDefault()
    const name = draft.trim()

    if (!name) {
      return
    }

    setItems((current) => [...current, { id: crypto.randomUUID(), name, done: false }])
    setDraft('')
  }

  function toggleItem(id) {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, done: !item.done } : item)),
    )
  }

  function removeItem(id) {
    setItems((current) => current.filter((item) => item.id !== id))
  }

  return (
    <div className={`pantry pantry--shop${menuOpen ? ' pantry--menu-open' : ''}`}>
      <div className="pantry__app">
        <AppHeader
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((open) => !open)}
          onBell={() => setToast('Уведомления появятся позже')}
        />

        <main className="content">
          <div className="shop__toolbar">
            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={() => setToast('Отправка списка в разработке')}
              aria-label="Поделиться списком"
            >
              <ShareIcon />
            </button>
          </div>

          <div className="shop__actions">
            <button
              className="btn btn--accent"
              type="button"
              onClick={() => setToast('Умный список в разработке')}
            >
              <SparkIcon />
              Сформировать умный список
            </button>

            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => setToast('Планирование дня покупок в разработке')}
            >
              <CalendarIcon />
              Запланировать день покупок
            </button>
          </div>

          {items.length === 0 ? (
            <div className="empty">
              <div className="empty__icon" aria-hidden="true">
                <BagIcon />
              </div>
              <p className="empty__title">Список пуст</p>
              <p className="empty__hint">Нажмите «Сформировать умный список»</p>
            </div>
          ) : (
            <ul className="shop__list">
              {items.map((item) => (
                <li className={`shop__item${item.done ? ' is-done' : ''}`} key={item.id}>
                  <button
                    className="shop__check"
                    type="button"
                    onClick={() => toggleItem(item.id)}
                    aria-pressed={item.done}
                    aria-label={item.done ? `Вернуть «${item.name}»` : `Отметить «${item.name}»`}
                  >
                    {item.done && <CheckIcon />}
                  </button>

                  <span className="shop__name">{item.name}</span>

                  <button
                    className="icon-btn icon-btn--danger"
                    type="button"
                    onClick={() => removeItem(item.id)}
                    aria-label={`Удалить «${item.name}»`}
                  >
                    <TrashIcon />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </main>
      </div>

      <form className="composer" onSubmit={addItem}>
        <div className="composer__inner">
          <input
            className="composer__input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Добавить в список..."
            aria-label="Добавить в список"
          />
          <button className="composer__add" type="submit" aria-label="Добавить">
            <PlusIcon />
          </button>
        </div>
      </form>

      <PantryDock
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onSignOut={signOut}
        onSelectTab={(title) => setToast(`Раздел «${title}» в разработке`)}
      />

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
