import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { pantryApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AddProductDialog } from '../components/AddProductDialog.jsx'
import { EditProductDialog } from '../components/EditProductDialog.jsx'
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
  const [editTarget, setEditTarget] = useState(null)
  const [consumeTarget, setConsumeTarget] = useState(null)
  const [wasteTarget, setWasteTarget] = useState(null)
  const [selecting, setSelecting] = useState(false)
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [bulkAction, setBulkAction] = useState(null)
  const [bulkPending, setBulkPending] = useState(false)
  const [bulkError, setBulkError] = useState('')
  const [toast, setToast] = useToast()
  const categoryChipsRef = useHorizontalScroll()
  const placeChipsRef = useHorizontalScroll()
  const location = useLocation()
  const navigate = useNavigate()
  const [attentionTick, setAttentionTick] = useState(0)
  const scrolledAttention = useRef(0)

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

  const filtersActive =
    query.trim() !== '' || activeCategory !== 'all' || activePlace !== 'all'

  function resetFilters() {
    setQuery('')
    setActiveCategory('all')
    setActivePlace('all')
  }

  function showAttention() {
    if (stats.expired + stats.soon === 0) {
      setToast('Всё в порядке, сроки не горят')
      return
    }

    resetFilters()
    setAttentionTick((tick) => tick + 1)
  }

  useEffect(() => {
    if (!location.state?.attention || state !== 'ready') {
      return
    }

    navigate('.', { replace: true, state: null })
    showAttention()
  }, [location.state, state])

  useEffect(() => {
    if (attentionTick === 0 || scrolledAttention.current === attentionTick || state !== 'ready') {
      return
    }

    const id = stats.expired > 0 ? 'group-expired' : 'group-soon'
    const node = document.getElementById(id)
    if (!node) {
      return
    }

    node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    scrolledAttention.current = attentionTick
  }, [attentionTick, state, stats.expired, stats.soon])

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

  function handleBatchSaved(items, close) {
    const count = items.length
    setToast(count === 1 ? `«${items[0].name}» добавлен` : `Добавлено ${count}`)
    notifyPurchaseChanged()
    if (close) {
      setAddOpen(false)
    }
  }

  async function handleCreated(item) {
    setAddOpen(false)
    let merged = false
    setProducts((current) => {
      const index = current.findIndex((product) => product.id === item.id)
      if (index === -1) {
        return [...current, item]
      }
      merged = true
      return current.map((product) => (product.id === item.id ? item : product))
    })
    setToast(merged ? `«${item.name}» добавлено к такой же покупке` : `«${item.name}» добавлен`)
    notifyPurchaseChanged()

    try {
      // Продукт мог завести новую категорию — обновляем фильтры.
      setCategories(await pantryApi.categories())
    } catch {
      // не критично: список категорий обновится при следующей загрузке
    }
  }

  function stopSelecting() {
    setSelecting(false)
    setSelectedIds(new Set())
    setBulkAction(null)
    setBulkError('')
  }

  function toggleSelected(product) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(product.id)) {
        next.delete(product.id)
      } else {
        next.add(product.id)
      }
      return next
    })
  }

  const selectedProducts = products.filter((product) => selectedIds.has(product.id))

  async function confirmBulk() {
    const reason = bulkAction
    const queue = selectedProducts
    setBulkPending(true)
    setBulkError('')
    const done = []

    try {
      for (const product of queue) {
        const updated = await pantryApi.wasteProduct(groupId, product.id, {
          reason,
          quantity: reason === 'mistake' ? null : Number(product.remaining ?? product.quantity),
        })
        done.push(updated.id)
      }
    } catch (bulkFailure) {
      setBulkError(bulkFailure.message)
    } finally {
      setBulkPending(false)
    }

    if (done.length === 0) {
      return
    }

    const finished = new Set(done)
    setProducts((current) => current.filter((product) => !finished.has(product.id)))
    setSelectedIds((current) => {
      const next = new Set(current)
      for (const id of finished) {
        next.delete(id)
      }
      return next
    })
    notifyPurchaseChanged()
    setToast(
      reason === 'mistake'
        ? `Убрано как ошибка: ${done.length}`
        : `Списано: ${done.length}`,
    )

    if (done.length === queue.length) {
      stopSelecting()
    }
  }

  function handleEdited(item) {
    setEditTarget(null)
    replaceProduct(item)
    setToast(`«${item.name}» сохранён`)
    pantryApi.categories().then(setCategories).catch(() => {})
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
          onBell={showAttention}
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
            {(products.length > 0 || filtersActive) && (
              <div className="filters__tools">
                {products.length > 0 && (
                  <button
                    className={`filters__reset${selecting ? ' is-active' : ''}`}
                    type="button"
                    onClick={() => (selecting ? stopSelecting() : setSelecting(true))}
                  >
                    {selecting ? 'Готово' : 'Выбрать'}
                  </button>
                )}
                {filtersActive && (
                  <button className="filters__reset" type="button" onClick={resetFilters}>
                    Сбросить
                  </button>
                )}
              </div>
            )}
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
                    <section className={`group group--${group.key}`} id={`group-${group.key}`} key={group.key}>
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
                            onEdit={setEditTarget}
                            selecting={selecting}
                            selected={selectedIds.has(product.id)}
                            onToggle={toggleSelected}
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
          onBatchSaved={handleBatchSaved}
        />
      )}

      {editTarget && (
        <EditProductDialog
          groupId={groupId}
          product={editTarget}
          categories={categories}
          places={places}
          onClose={() => setEditTarget(null)}
          onSaved={handleEdited}
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

      {selecting && selectedProducts.length > 0 && (
        <div className="pickbar">
          <p className="pickbar__count">Выбрано {selectedProducts.length}</p>
          <button className="pickbar__btn" type="button" onClick={() => setBulkAction('spoiled')}>
            Списать
          </button>
          <button
            className="pickbar__btn pickbar__btn--danger"
            type="button"
            onClick={() => setBulkAction('mistake')}
          >
            Удалить как ошибку
          </button>
        </div>
      )}

      {bulkAction && (
        <div className="pickconfirm" role="dialog" aria-modal="true" aria-label="Подтверждение">
          <button
            className="pickconfirm__backdrop"
            type="button"
            aria-label="Закрыть"
            onClick={() => {
              if (!bulkPending) {
                setBulkAction(null)
                setBulkError('')
              }
            }}
          />
          <div className="pickconfirm__sheet">
            <p>
              {bulkAction === 'mistake'
                ? `Удалить ${selectedProducts.length} как ошибку? Записи исчезнут из кладовой.`
                : `Списать ${selectedProducts.length}? У каждого спишется весь остаток.`}
            </p>
            {bulkError && <p className="pickconfirm__error">{bulkError}</p>}
            <div className="pickconfirm__actions">
              <button className="btn btn--ghost" type="button" onClick={() => setBulkAction(null)} disabled={bulkPending}>
                Отмена
              </button>
              <button className="btn btn--primary" type="button" onClick={confirmBulk} disabled={bulkPending}>
                {bulkPending ? 'Записываем...' : bulkAction === 'mistake' ? 'Удалить' : 'Списать'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
