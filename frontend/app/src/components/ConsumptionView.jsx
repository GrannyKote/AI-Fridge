import { useCallback, useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { categoryView, formatNumber } from '../lib/pantry.js'
import { useHorizontalScroll } from '../lib/useHorizontalScroll.js'
import { SparkIcon } from './icons.jsx'

const PERIODS = [
  { key: 'day', title: 'День', accusative: 'день' },
  { key: 'week', title: 'Неделя', accusative: 'неделю' },
  { key: 'month', title: 'Месяц', accusative: 'месяц' },
  { key: 'quarter', title: 'Квартал', accusative: 'квартал' },
  { key: 'year', title: 'Год', accusative: 'год' },
]

const KINDS = [
  { key: 'all', title: 'Все' },
  { key: 'consumption', title: 'Потребление' },
  { key: 'waste', title: 'Списание', tone: 'waste' },
]

function amount(value, unit) {
  return unit ? `${formatNumber(value)} ${unit}` : formatNumber(value)
}

// За сутки средний расход в день совпадает с итогом, поэтому его не дублируем.
function usageText(series, unit, days) {
  const total = amount(series.total, unit)

  if (days === 1) {
    return `${total} за сутки`
  }

  return `~${amount(series.per_day, unit)}/день · ${total} за ${days} дн.`
}

function totalOf(product) {
  return (product.consumption?.total ?? 0) + (product.waste?.total ?? 0)
}

function Chips({ items, value, onSelect, label }) {
  const ref = useHorizontalScroll()

  return (
    <nav className="chips" ref={ref} aria-label={label}>
      {items.map((item) => (
        <button
          key={item.key}
          className={`chip${item.tone ? ` chip--${item.tone}` : ''}${
            item.key === value ? ' is-active' : ''
          }`}
          type="button"
          onClick={() => onSelect(item.key)}
        >
          {item.title}
        </button>
      ))}
    </nav>
  )
}

function Track({ value, max, tone }) {
  return (
    <span className="usage__track">
      <i
        className={`usage__fill${tone === 'waste' ? ' usage__fill--waste' : ''}`}
        style={{ width: `${max > 0 ? (value / max) * 100 : 0}%` }}
      />
    </span>
  )
}

function Sparkline({ buckets, tone }) {
  const max = Math.max(...buckets, 0)

  return (
    <div className="spark" aria-hidden="true">
      {buckets.map((value, index) => {
        const ratio = max > 0 ? value / max : 0

        return (
          <span
            className={`spark__bar${tone === 'waste' ? ' spark__bar--waste' : ''}`}
            key={index}
            style={{
              height: `${Math.max(ratio * 100, 3)}%`,
              opacity: value > 0 ? 0.4 + ratio * 0.6 : 0.35,
            }}
          />
        )
      })}
    </div>
  )
}

function Series({ series, unit, days, tone, label }) {
  return (
    <>
      <p className={`ucard__meta${tone === 'waste' ? ' ucard__meta--waste' : ''}`}>
        {label && <span className="ucard__tag">{label}</span>}
        {usageText(series, unit, days)}
      </p>
      <Sparkline buckets={series.buckets} tone={tone} />
    </>
  )
}

export function ConsumptionView({ groupId, refreshKey }) {
  const [period, setPeriod] = useState('week')
  const [kind, setKind] = useState('all')
  const [stats, setStats] = useState(null)
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setState('loading')

    try {
      setStats(await pantryApi.usage(groupId, period))
      setState('ready')
    } catch (loadError) {
      setError(loadError.message)
      setState('error')
    }
  }, [groupId, period])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  const selected = PERIODS.find((item) => item.key === period)
  const withEaten = kind !== 'waste'
  const withWasted = kind !== 'consumption'

  const categories = (stats?.categories ?? [])
    .map((category) => ({
      ...category,
      consumed: withEaten ? category.consumed : 0,
      wasted: withWasted ? category.wasted : 0,
    }))
    .filter((category) => category.consumed > 0 || category.wasted > 0)
    .sort((first, second) => second.consumed + second.wasted - (first.consumed + first.wasted))

  const maxCategory = Math.max(
    ...categories.flatMap((category) => [category.consumed, category.wasted]),
    0,
  )

  const products = (stats?.products ?? [])
    .map((product) => ({
      ...product,
      consumption: withEaten ? product.consumption : null,
      waste: withWasted ? product.waste : null,
    }))
    .filter((product) => product.consumption || product.waste)
    .sort((first, second) => totalOf(second) - totalOf(first))

  return (
    <>
      <div className="usage">
        <h2 className="usage__label">Период отображения</h2>
        <Chips items={PERIODS} value={period} onSelect={setPeriod} label="Период статистики" />
      </div>

      <div className="usage">
        <h2 className="usage__label">Тип списания</h2>
        <Chips items={KINDS} value={kind} onSelect={setKind} label="Тип списания" />
      </div>

      {state === 'loading' && <p className="pantry__message">Считаем расход...</p>}

      {state === 'error' && (
        <div className="pantry__message">
          <p>{error}</p>
          <button className="btn btn--ghost" type="button" onClick={load}>
            Повторить
          </button>
        </div>
      )}

      {state === 'ready' && products.length === 0 && (
        <p className="pantry__message">
          За выбранный период записей нет — отмечайте съеденные и испорченные продукты в кладовой.
        </p>
      )}

      {state === 'ready' && products.length > 0 && (
        <>
          <section className="panel">
            <header className="panel__head">
              <h2 className="panel__title">
                <SparkIcon />
                По категориям
              </h2>
              <span className="panel__note">за {selected.accusative}</span>
            </header>

            <ul className="usage__list">
              {categories.map((category) => (
                <li className="usage__row" key={category.name}>
                  <span className="usage__emoji" aria-hidden="true">
                    {categoryView(category.name, category.id ?? 0).emoji}
                  </span>
                  <span className="usage__name">{category.name}</span>
                  <span className="usage__values">
                    {category.consumed > 0 && (
                      <span className="usage__value">
                        {amount(category.consumed, category.unit)}
                      </span>
                    )}
                    {category.wasted > 0 && (
                      <span className="usage__value usage__value--waste">
                        {amount(category.wasted, category.unit)}
                      </span>
                    )}
                  </span>

                  {category.consumed > 0 && <Track value={category.consumed} max={maxCategory} />}
                  {category.wasted > 0 && (
                    <Track value={category.wasted} max={maxCategory} tone="waste" />
                  )}
                </li>
              ))}
            </ul>
          </section>

          <div className="usage">
            <h2 className="usage__label">По продуктам — {selected.title}</h2>

            <div className="group__list">
              {products.map((product) => {
                const entries =
                  (product.consumption?.entries ?? 0) + (product.waste?.entries ?? 0)
                const onlyWaste = !product.consumption && product.waste

                return (
                  <article className="ucard" key={product.name}>
                    <header className="ucard__head">
                      <span className="usage__emoji" aria-hidden="true">
                        {categoryView(product.category, product.category_id ?? 0).emoji}
                      </span>
                      <h3 className="ucard__title">{product.name}</h3>
                      <span className={`ucard__badge${onlyWaste ? ' ucard__badge--waste' : ''}`}>
                        {entries} изм.
                      </span>
                    </header>

                    {product.consumption && (
                      <Series
                        series={product.consumption}
                        unit={product.unit}
                        days={stats.period_days}
                        label={kind === 'all' ? 'Употреблено' : ''}
                      />
                    )}

                    {product.waste && (
                      <Series
                        series={product.waste}
                        unit={product.unit}
                        days={stats.period_days}
                        tone="waste"
                        label={kind === 'all' ? 'Списано' : ''}
                      />
                    )}
                  </article>
                )
              })}
            </div>
          </div>
        </>
      )}
    </>
  )
}
