import { useCallback, useEffect, useMemo, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { ConsumptionView } from '../components/ConsumptionView.jsx'
import { ForecastCard } from '../components/ForecastCard.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { BarsIcon, ClockIcon, WarningIcon } from '../components/icons.jsx'
import { statusOf } from '../lib/pantry.js'
import { usePurchaseChanged } from '../lib/purchaseEvents.js'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/forecast.css'

const TABS = [
  { key: 'dates', title: 'Сроки', icon: <WarningIcon /> },
  { key: 'usage', title: 'Потребление', icon: <BarsIcon /> },
]

export default function ForecastPage() {
  const { user, signOut } = useAuth()
  const groupId = user.groups?.[0]?.id

  const [products, setProducts] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [tab, setTab] = useState('dates')
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useToast()

  const load = useCallback(
    async (silent = false) => {
      if (!groupId) {
        setState('error')
        setError('У пользователя нет группы, прогноз построить не получится')
        return
      }

      if (silent !== true) {
        setState('loading')
      }

      try {
        setProducts(await pantryApi.products(groupId))
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

  const sections = useMemo(() => {
    const soon = []
    const later = []

    for (const product of products) {
      if (statusOf(product) === 'fresh') {
        later.push(product)
      } else {
        soon.push(product)
      }
    }

    return [
      { key: 'soon', title: 'Скоро испортится', icon: <WarningIcon />, items: soon },
      { key: 'fresh', title: 'Позже', icon: <ClockIcon />, items: later },
    ]
  }, [products])

  const alerts = useMemo(
    () => products.filter((product) => statusOf(product) !== 'fresh').length,
    [products],
  )

  return (
    <div className={`pantry${menuOpen ? ' pantry--menu-open' : ''}`}>
      <div className="pantry__app">
        <AppHeader
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((open) => !open)}
          alerts={alerts}
          onToast={setToast}
        />

        <main className="content">
          <div className="segmented" role="tablist" aria-label="Тип прогноза">
            {TABS.map((item) => (
              <button
                key={item.key}
                className={`segmented__item${tab === item.key ? ' is-active' : ''}`}
                type="button"
                role="tab"
                aria-selected={tab === item.key}
                onClick={() => setTab(item.key)}
              >
                {item.icon}
                {item.title}
              </button>
            ))}
          </div>

          {tab === 'dates' && state === 'loading' && (
            <p className="pantry__message">Считаем сроки...</p>
          )}

          {tab === 'dates' && state === 'error' && (
            <div className="pantry__message">
              <p>{error}</p>
              <button className="btn btn--ghost" type="button" onClick={() => load()}>
                Повторить
              </button>
            </div>
          )}

          {state === 'ready' && tab === 'dates' && (
            <>
              <div className="groups">
                {sections.map((section) =>
                  section.items.length === 0 ? null : (
                    <section className={`group group--${section.key}`} key={section.key}>
                      <h2 className="group__head">
                        {section.icon}
                        {section.title} · {section.items.length}
                      </h2>
                      <div className="group__list">
                        {section.items.map((product) => (
                          <ForecastCard key={product.id} product={product} />
                        ))}
                      </div>
                    </section>
                  ),
                )}
              </div>

              {products.length === 0 && (
                <p className="pantry__message">
                  Кладовая пуста — прогнозировать пока нечего.
                </p>
              )}
            </>
          )}

          {tab === 'usage' &&
            (groupId ? (
              <ConsumptionView groupId={groupId} />
            ) : (
              <p className="pantry__message">{error}</p>
            ))}
        </main>
      </div>

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
