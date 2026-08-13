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

function amount(value, unit) {
  return unit ? `${formatNumber(value)} ${unit}` : formatNumber(value)
}

// За сутки средний расход в день совпадает с итогом, поэтому его не дублируем.
function usageText(product, days) {
  const total = amount(product.total, product.unit)

  if (days === 1) {
    return `${total} за сутки`
  }

  return `~${amount(product.per_day, product.unit)}/день · ${total} за ${days} дн.`
}

function Sparkline({ buckets }) {
  const max = Math.max(...buckets, 0)

  return (
    <div className="spark" aria-hidden="true">
      {buckets.map((value, index) => {
        const ratio = max > 0 ? value / max : 0

        return (
          <span
            className="spark__bar"
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

export function ConsumptionView({ groupId, refreshKey }) {
  const [period, setPeriod] = useState('week')
  const [stats, setStats] = useState(null)
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const chipsRef = useHorizontalScroll()

  const load = useCallback(async () => {
    setState('loading')

    try {
      setStats(await pantryApi.consumption(groupId, period))
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
  const maxCategory = Math.max(...(stats?.categories ?? []).map((item) => item.quantity), 0)

  return (
    <>
      <div className="usage">
        <h2 className="usage__label">Период отображения</h2>

        <nav className="chips" ref={chipsRef} aria-label="Период статистики">
          {PERIODS.map((item) => (
            <button
              key={item.key}
              className={`chip${item.key === period ? ' is-active' : ''}`}
              type="button"
              onClick={() => setPeriod(item.key)}
            >
              {item.title}
            </button>
          ))}
        </nav>
      </div>

      {state === 'loading' && <p className="pantry__message">Считаем потребление...</p>}

      {state === 'error' && (
        <div className="pantry__message">
          <p>{error}</p>
          <button className="btn btn--ghost" type="button" onClick={load}>
            Повторить
          </button>
        </div>
      )}

      {state === 'ready' && stats.products.length === 0 && (
        <p className="pantry__message">
          Записей о потреблении пока нет — отмечайте съеденные продукты в кладовой.
        </p>
      )}

      {state === 'ready' && stats.products.length > 0 && (
        <>
          {stats.categories.length > 0 && (
            <section className="panel">
              <header className="panel__head">
                <h2 className="panel__title">
                  <SparkIcon />
                  По категориям
                </h2>
                <span className="panel__note">за {selected.accusative}</span>
              </header>

              <ul className="usage__list">
                {stats.categories.map((category) => (
                  <li className="usage__row" key={category.name}>
                    <span className="usage__emoji" aria-hidden="true">
                      {categoryView(category.name, category.id ?? 0).emoji}
                    </span>
                    <span className="usage__name">{category.name}</span>
                    <span className="usage__value">{amount(category.quantity, category.unit)}</span>
                    <span className="usage__track">
                      <i
                        className="usage__fill"
                        style={{
                          width: `${maxCategory > 0 ? (category.quantity / maxCategory) * 100 : 0}%`,
                        }}
                      />
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="usage">
            <h2 className="usage__label">По продуктам — {selected.title}</h2>

            <div className="group__list">
              {stats.products.map((product) => (
                <article className="ucard" key={product.name}>
                  <header className="ucard__head">
                    <span className="usage__emoji" aria-hidden="true">
                      {categoryView(product.category, product.category_id ?? 0).emoji}
                    </span>
                    <h3 className="ucard__title">{product.name}</h3>
                    <span className="ucard__badge">{product.entries} изм.</span>
                  </header>

                  <p className="ucard__meta">{usageText(product, stats.period_days)}</p>

                  <Sparkline buckets={product.buckets} />
                </article>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  )
}
