import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { pantryApi, shoppingApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { mergeMatchingProducts } from '../lib/pantry.js'
import { notifyPurchaseChanged, usePurchaseChanged } from '../lib/purchaseEvents.js'
import { CheckoutDialog } from './CheckoutDialog.jsx'
import { FeedbackDialog } from './FeedbackDialog.jsx'
import { NewsDialog } from './NewsDialog.jsx'
import { NotificationsDialog } from './NotificationsDialog.jsx'
import { PlanPurchaseDialog } from './PlanPurchaseDialog.jsx'
import { PlannedPurchaseBanner } from './PlannedPurchaseBanner.jsx'
import { BellIcon, FeedbackIcon, NewsIcon } from './icons.jsx'

export function AppHeader({ onToast }) {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const groupId = user.groups?.[0]?.id
  const showPlan = pathname !== '/settings'

  const [planDate, setPlanDate] = useState(null)
  const [items, setItems] = useState([])
  // Продукты из групп «Просрочено» и «Скоро испортится»: счётчик и список в форме.
  const [attention, setAttention] = useState([])
  const [dialogProducts, setDialogProducts] = useState([])
  const [planOpen, setPlanOpen] = useState(false)
  const [checkoutOpen, setCheckoutOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [newsOpen, setNewsOpen] = useState(false)
  const [feedbackOpen, setFeedbackOpen] = useState(false)

  const load = useCallback(async () => {
    if (!groupId) {
      setPlanDate(null)
      setItems([])
      setAttention([])
      return
    }

    const [header, purchaseList, reminders] = await Promise.all([
      shoppingApi.header(groupId).catch(() => null),
      shoppingApi.list(groupId).catch(() => []),
      pantryApi.reminders(groupId).catch(() => []),
    ])

    setPlanDate(header?.plan_date ?? null)
    setItems(purchaseList)
    setAttention(mergeMatchingProducts(reminders))
  }, [groupId])

  useEffect(() => {
    load()
  }, [load])

  usePurchaseChanged(load)

  const markRemindersSeen = useCallback(async () => {
    if (!groupId) {
      return
    }

    await pantryApi.markRemindersSeen(groupId).catch(() => {})
    await load()
  }, [groupId, load])

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
              onClick={() => {
                setDialogProducts(attention)
                setNotificationsOpen(true)
              }}
              aria-label={
                attention.length > 0
                  ? `Требуют внимания, ${attention.length}`
                  : 'Требуют внимания'
              }
              aria-expanded={notificationsOpen}
            >
              <BellIcon />
              {attention.length > 0 && (
                <span className="icon-btn__badge">{attention.length}</span>
              )}
            </button>

            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={() => setNewsOpen(true)}
              aria-label="Новости"
              aria-expanded={newsOpen}
            >
              <NewsIcon />
            </button>

            <button
              className="icon-btn icon-btn--round"
              type="button"
              onClick={() => setFeedbackOpen(true)}
              aria-label="Обратная связь"
              aria-expanded={feedbackOpen}
            >
              <FeedbackIcon />
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
        <NotificationsDialog
          products={dialogProducts}
          onClose={() => setNotificationsOpen(false)}
          onViewed={markRemindersSeen}
          onGo={() => {
            setNotificationsOpen(false)
            navigate('/')
          }}
        />
      )}

      {newsOpen && <NewsDialog onClose={() => setNewsOpen(false)} />}

      {feedbackOpen && (
        <FeedbackDialog
          onClose={() => setFeedbackOpen(false)}
          onSent={() => {
            setFeedbackOpen(false)
            toast('Спасибо за отзыв')
          }}
        />
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
