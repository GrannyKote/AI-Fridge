import { useCallback, useEffect, useState } from 'react'
import { pantryApi, shoppingApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AddPurchaseDialog } from '../components/AddPurchaseDialog.jsx'
import { AppHeader } from '../components/AppHeader.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { PlanPurchaseDialog } from '../components/PlanPurchaseDialog.jsx'
import { BagIcon, CalendarIcon, ShareIcon, SparkIcon, TrashIcon } from '../components/icons.jsx'
import { formatAmount } from '../lib/pantry.js'
import { notifyPurchaseChanged, usePurchaseChanged } from '../lib/purchaseEvents.js'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/shopping.css'

export default function ShoppingPage() {
  const { user, signOut } = useAuth()
  const groupId = user.groups?.[0]?.id

  const [items, setItems] = useState([])
  const [categories, setCategories] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [planOpen, setPlanOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [toast, setToast] = useToast()

  const load = useCallback(
    async (silent = false) => {
      if (!groupId) {
        setState('error')
        setError('У пользователя нет группы, список покупок показать не получится')
        return
      }

      if (silent !== true) {
        setState('loading')
      }

      try {
        const [purchaseList, categoryList] = await Promise.all([
          shoppingApi.list(groupId),
          pantryApi.categories(),
        ])
        setItems(purchaseList)
        setCategories(categoryList)
        setState('ready')
      } catch (loadError) {
        setError(loadError.message)
        setState('error')
      }
    },
    [groupId],
  )

  useEffect(() => {
    load()
  }, [load])

  usePurchaseChanged(useCallback(() => load(true), [load]))

  function handleCreated(item) {
    setAddOpen(false)
    setItems((current) => [...current, item])
    setToast(`«${item.name}» добавлен в список`)
    notifyPurchaseChanged()
  }

  async function handleDelete(item) {
    if (deletingId) {
      return
    }

    setDeletingId(item.id)
    try {
      await shoppingApi.remove(groupId, item.id)
      setItems((current) => current.filter((entry) => entry.id !== item.id))
      setToast(`«${item.name}» удалён из списка`)
      notifyPurchaseChanged()
    } catch (deleteError) {
      setToast(deleteError.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className={`pantry pantry--shop${menuOpen ? ' pantry--menu-open' : ''}`}>
      <div className="pantry__app">
        <AppHeader
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((open) => !open)}
          onToast={setToast}
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
              onClick={() => setPlanOpen(true)}
            >
              <CalendarIcon />
              Запланировать день покупок
            </button>
          </div>

          {state === 'loading' && <p className="pantry__message">Загружаем список...</p>}

          {state === 'error' && (
            <div className="pantry__message">
              <p>{error}</p>
              <button className="btn btn--ghost" type="button" onClick={() => load()}>
                Повторить
              </button>
            </div>
          )}

          {state === 'ready' && items.length === 0 && (
            <div className="empty">
              <div className="empty__icon" aria-hidden="true">
                <BagIcon />
              </div>
              <p className="empty__title">Список пуст</p>
              <p className="empty__hint">Нажмите «Добавить в список»</p>
            </div>
          )}

          {state === 'ready' && items.length > 0 && (
            <ul className="shop__list">
              {items.map((item) => (
                <li className="shop__item" key={item.id}>
                  <span className="shop__body">
                    <span className="shop__name">{item.name}</span>
                    <span className="shop__meta">{formatAmount(item)}</span>
                  </span>
                  <button
                    className="icon-btn icon-btn--danger"
                    type="button"
                    onClick={() => handleDelete(item)}
                    disabled={deletingId === item.id}
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

      <div className="composer">
        <div className="composer__inner">
          <button className="btn btn--primary" type="button" onClick={() => setAddOpen(true)}>
            Добавить в список
          </button>
        </div>
      </div>

      <PantryDock
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onSignOut={signOut}
        onSelectTab={(title) => setToast(`Раздел «${title}» в разработке`)}
      />

      {addOpen && (
        <AddPurchaseDialog
          groupId={groupId}
          categories={categories}
          onClose={() => setAddOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {planOpen && (
        <PlanPurchaseDialog
          groupId={groupId}
          onClose={() => setPlanOpen(false)}
          onPlanned={(label) => {
            setPlanOpen(false)
            setToast(`День покупок запланирован на ${label}`)
            notifyPurchaseChanged()
          }}
        />
      )}

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
