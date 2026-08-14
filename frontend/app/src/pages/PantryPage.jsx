import { useCallback, useEffect, useMemo, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AddProductDialog } from '../components/AddProductDialog.jsx'
import { AppHeader } from '../components/AppHeader.jsx'
import { ConsumeDialog } from '../components/ConsumeDialog.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { ProductCard } from '../components/ProductCard.jsx'
import { WasteDialog } from '../components/WasteDialog.jsx'
import { CheckIcon, ClockIcon, SearchIcon, WarningIcon } from '../components/icons.jsx'
import { formatAmount, statusOf } from '../lib/pantry.js'
import { notifyPurchaseChanged, usePurchaseChanged } from '../lib/purchaseEvents.js'
import { useHorizontalScroll } from '../lib/useHorizontalScroll.js'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'

const GROUPS = [
  { key: 'expired', title: 'Просрочено', icon: <WarningIcon /> },
  { key: 'soon', title: 'Скоро испортится', icon: <ClockIcon /> },
  { key: 'fresh', title: 'Свежие', icon: <CheckIcon /> },
]

export default function PantryPage() {
  const { user, signOut } = useAuth()
  const groupId = user.groups?.[0]?.id

  const [categories, setCategories] = useState([])
  const [places, setPlaces] = useState([])
  const [products, setProducts] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('all')
  const [activePlace, setActivePlace] = useState('all')
  const [menuOpen, setMenuOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [consumeTarget, setConsumeTarget] = useState(null)
  const [wasteTarget, setWasteTarget] = useState(null)
  const [toast, setToast] = useToast()
  const categoryChipsRef = useHorizontalScroll()
  const placeChipsRef = useHorizontalScroll()

  const load = useCallback(
    async (silent = false) => {
      if (!groupId) {
        setState('error')
        setError('У пользователя нет группы, кладовую показать не получится')
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

  const stats = useMemo(() => {
    const counters = { total: products.length, soon: 0, expired: 0 }

    for (const product of products) {
      const status = statusOf(product)
      if (status !== 'fresh') {
        counters[status] += 1
      }
    }

    return counters
  }, [products])

  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase()

    return products.filter((product) => {
      const matchesCategory =
        activeCategory === 'all' || product.category_id === activeCategory
      const matchesPlace =
        activePlace === 'all' || product.storage_place_id === activePlace
      return (
        matchesCategory && matchesPlace && product.name.toLowerCase().includes(normalized)
      )
    })
  }, [products, query, activeCategory, activePlace])

  async function handleCreated(item) {
    setAddOpen(false)
    setProducts((current) => [...current, item])
    setToast(`«${item.name}» добавлен`)
    notifyPurchaseChanged()

    try {
      // Продукт мог завести новую категорию — обновляем фильтры.
      setCategories(await pantryApi.categories())
    } catch {
      // не критично: список категорий обновится при следующей загрузке
    }
  }

  function handleCardAction(product, action) {
    if (action === 'use') {
      setConsumeTarget(product)
    } else {
      setWasteTarget(product)
    }
  }

  function replaceProduct(item) {
    setProducts((current) =>
      current.map((product) => (product.id === item.id ? item : product)),
    )
  }

  function dropProduct(item) {
    setProducts((current) => current.filter((product) => product.id !== item.id))
  }

  function handleConsumed(item) {
    setConsumeTarget(null)
    notifyPurchaseChanged()

    // Продукт закончился — карточке в кладовой больше не место.
    if (item.is_over) {
      dropProduct(item)
      setToast(
        item.is_consumed ? `«${item.name}» употреблён полностью` : `«${item.name}» закончился`,
      )
      return
    }

    replaceProduct(item)
    setToast(`Осталось ${formatAmount(item)} «${item.name}»`)
  }

  function handleWasted(item, reason) {
    setWasteTarget(null)
    notifyPurchaseChanged()

    if (reason === 'mistake') {
      dropProduct(item)
      setToast(`«${item.name}» убран как ошибочная запись`)
      return
    }

    if (item.is_over) {
      dropProduct(item)
      setToast(`«${item.name}» списан полностью`)
      return
    }

    replaceProduct(item)
    setToast(`Осталось ${formatAmount(item)} «${item.name}»`)
  }

  return (
    <div className={`pantry${menuOpen ? ' pantry--menu-open' : ''}`}>
      <div className="pantry__app">
        <AppHeader
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((open) => !open)}
          alerts={stats.expired + stats.soon}
          onBell={() =>
            setToast(
              stats.expired + stats.soon > 0
                ? `Требуют внимания: ${stats.expired + stats.soon}`
                : 'Всё в порядке, сроки не горят',
            )
          }
          onToast={setToast}
        />

        <main className="content">
          <section className="stats" aria-label="Сводка по кладовой">
            <article className="stat">
              <p className="stat__value">{stats.total}</p>
              <p className="stat__label">Продуктов</p>
            </article>
            <article className="stat">
              <p className="stat__value stat__value--warning">{stats.soon}</p>
              <p className="stat__label">Истекает</p>
            </article>
            <article className="stat">
              <p className="stat__value stat__value--danger">{stats.expired}</p>
              <p className="stat__label">Просрочено</p>
            </article>
          </section>

          <form className="search" role="search" onSubmit={(event) => event.preventDefault()}>
            <SearchIcon className="search__icon" />
            <input
              className="search__input"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Поиск продукта..."
              autoComplete="off"
              aria-label="Поиск продукта"
            />
          </form>

          <div className="filters">
            <nav className="chips" aria-label="Категории" ref={categoryChipsRef}>
              <button
                className={`chip${activeCategory === 'all' ? ' is-active' : ''}`}
                type="button"
                onClick={() => setActiveCategory('all')}
              >
                Все
              </button>
              {categories.map((category) => (
                <button
                  key={category.id}
                  className={`chip${activeCategory === category.id ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => setActiveCategory(category.id)}
                >
                  {category.name}
                </button>
              ))}
            </nav>

            <nav className="chips" aria-label="Места хранения" ref={placeChipsRef}>
              <button
                className={`chip${activePlace === 'all' ? ' is-active' : ''}`}
                type="button"
                onClick={() => setActivePlace('all')}
              >
                Все
              </button>
              {places.map((place) => (
                <button
                  key={place.id}
                  className={`chip${activePlace === place.id ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => setActivePlace(place.id)}
                >
                  {place.name}
                </button>
              ))}
            </nav>
          </div>

          {state === 'loading' && <p className="pantry__message">Загружаем кладовую...</p>}

          {state === 'error' && (
            <div className="pantry__message">
              <p>{error}</p>
              <button className="btn btn--ghost" type="button" onClick={() => load()}>
                Повторить
              </button>
            </div>
          )}

          {state === 'ready' && (
            <>
              <div className="groups">
                {GROUPS.map((group) => {
                  const items = visible.filter((product) => statusOf(product) === group.key)

                  if (items.length === 0) {
                    return null
                  }

                  return (
                    <section className={`group group--${group.key}`} key={group.key}>
                      <h2 className="group__head">
                        {group.icon}
                        {group.title} · {items.length}
                      </h2>
                      <div className="group__list">
                        {items.map((product) => (
                          <ProductCard
                            key={product.id}
                            product={product}
                            onAction={handleCardAction}
                          />
                        ))}
                      </div>
                    </section>
                  )
                })}
              </div>

              {visible.length === 0 && (
                <p className="pantry__message">
                  {products.length === 0
                    ? 'Кладовая пуста. Добавьте первый продукт.'
                    : 'Ничего не нашлось. Попробуйте другой запрос.'}
                </p>
              )}
            </>
          )}
        </main>
      </div>

      <PantryDock
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onSignOut={signOut}
        onAdd={() => {
          setMenuOpen(false)
          setAddOpen(true)
        }}
        onSelectTab={(title) => setToast(`Раздел «${title}» в разработке`)}
      />

      {addOpen && (
        <AddProductDialog
          groupId={groupId}
          categories={categories}
          onClose={() => setAddOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {consumeTarget && (
        <ConsumeDialog
          groupId={groupId}
          product={consumeTarget}
          onClose={() => setConsumeTarget(null)}
          onConsumed={handleConsumed}
        />
      )}

      {wasteTarget && (
        <WasteDialog
          groupId={groupId}
          product={wasteTarget}
          onClose={() => setWasteTarget(null)}
          onWasted={handleWasted}
        />
      )}

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
