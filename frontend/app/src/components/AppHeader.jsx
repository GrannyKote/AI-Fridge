import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { shoppingApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { notifyPurchaseChanged, usePurchaseChanged } from '../lib/purchaseEvents.js'
import { CheckoutDialog } from './CheckoutDialog.jsx'
import { NotificationsDialog } from './NotificationsDialog.jsx'
import { PlanPurchaseDialog } from './PlanPurchaseDialog.jsx'
import { PlannedPurchaseBanner } from './PlannedPurchaseBanner.jsx'
import { BellIcon, MenuIcon } from './icons.jsx'

export function AppHeader({ menuOpen, onToggleMenu, alerts = 0, onToast }) {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const groupId = user.groups?.[0]?.id
  const showPlan = pathname !== '/settings'

  const [planDate, setPlanDate] = useState(null)
  const [items, setItems] = useState([])
  const [planOpen, setPlanOpen] = useState(false)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  const loadPlan = useCallback(async () => {
    if (!groupId) {
      setPlanDate(null)
      setItems([])
      return
    }

    const [header, purchaseList] = await Promise.all([
      shoppingApi.header(groupId).catch(() => null),
      shoppingApi.list(groupId).catch(() => []),
    ])

    setPlanDate(header?.plan_date ?? null)
    setItems(purchaseList)
  }, [groupId])

  useEffect(() => {
    loadPlan()
  }, [loadPlan])

  usePurchaseChanged(loadPlan)

  function toast(message) {
    onToast?.(message)
  }

  return (
    <>
      <header className="app-header">
        <div className="topbar">
          <h1 className="topbar__name">{user.login}</h1>

          <div className="topbar__actions">
            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={onToggleMenu}
              aria-label={menuOpen ? 'Скрыть меню' : 'Показать меню'}
              aria-expanded={menuOpen}
            >
              <MenuIcon />
            </button>

            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={() => setNotificationsOpen(true)}
              aria-label={alerts > 0 ? `Уведомления, ${alerts}` : 'Уведомления'}
              aria-expanded={notificationsOpen}
            >
              <BellIcon />
              {alerts > 0 && <span className="icon-btn__badge">{alerts}</span>}
            </button>
          </div>
        </div>

        {showPlan && planDate && (
          <div className="app-header__plan">
            <PlannedPurchaseBanner
              planDate={planDate}
              onChangeDate={() => setPlanOpen(true)}
              onCalculate={() => {
                if (items.length === 0) {
                  toast('Сначала добавьте товары в список')
                  return
                }

                setCheckoutOpen(true)
              }}
            />
          </div>
        )}
      </header>

      {notificationsOpen && (
        <NotificationsDialog onClose={() => setNotificationsOpen(false)} />
      )}

      {planOpen && groupId && (
        <PlanPurchaseDialog
          groupId={groupId}
          onClose={() => setPlanOpen(false)}
          onPlanned={(label) => {
            setPlanOpen(false)
            toast(`День покупок запланирован на ${label}`)
            notifyPurchaseChanged()
          }}
        />
      )}

      {checkoutOpen && groupId && (
        <CheckoutDialog
          groupId={groupId}
          items={items}
          onClose={() => setCheckoutOpen(false)}
          onDone={(count) => {
            setCheckoutOpen(false)
            toast(count === 1 ? 'Товар добавлен в кладовую' : `В кладовую добавлено: ${count}`)
            notifyPurchaseChanged()
          }}
        />
      )}
    </>
  )
}
