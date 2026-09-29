import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { pantryApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { ConsumptionView } from '../components/ConsumptionView.jsx'
import { EditProductDialog } from '../components/EditProductDialog.jsx'
import { ForecastCard } from '../components/ForecastCard.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { BarsIcon, ClockIcon, WarningIcon } from '../components/icons.jsx'
import { statusOf } from '../lib/pantry.js'
import { notifyPurchaseChanged, usePurchaseChanged } from '../lib/purchaseEvents.js'
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
  const [categories, setCategories] = useState([])
  const [places, setPlaces] = useState([])
  const [editTarget, setEditTarget] = useState(null)
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [tab, setTab] = useState('dates')
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useToast()
  const navigate = useNavigate()

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
        const [categoryList, placeList, productList] = await Promise.all([
          pantryApi.categories(),
          pantryApi.places(),
          pantryApi.products(groupId),
        ])
        setCategories(categoryList)
        setPlaces(placeList)
        setProducts(productList)
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
          onBell={() => {
            if (alerts > 0) {
              navigate('/', { state: { attention: true } })
              return
            }
            setToast('Всё в порядке, сроки не горят')
          }}
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
                          <ForecastCard key={product.id} product={product} onEdit={setEditTarget} />
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

      {editTarget && (
        <EditProductDialog
          groupId={groupId}
          product={editTarget}
          categories={categories}
          places={places}
          onClose={() => setEditTarget(null)}
          onSaved={(item) => {
            setEditTarget(null)
            setProducts((current) =>
              current.map((product) => (product.id === item.id ? item : product)),
            )
            setToast(`«${item.name}» сохранён`)
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
