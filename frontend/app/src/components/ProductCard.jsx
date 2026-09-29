import { TrashIcon, UtensilsIcon } from './icons.jsx'
import { badgeTextOf, categoryView, formatAmount, statusOf } from '../lib/pantry.js'

export function ProductCard({ product, onAction, selecting = false, selected = false, onToggle }) {
  const status = statusOf(product)
  const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)

  return (
    <article
      className={`card${status === 'expired' ? ' card--expired' : ''}${selected ? ' card--picked' : ''}`}
      onClick={selecting ? () => onToggle(product) : undefined}
      role={selecting ? 'checkbox' : undefined}
      aria-checked={selecting ? selected : undefined}
    >
      <div className={`card__thumb card__thumb--${tone}`} aria-hidden="true">
        {emoji}
      </div>

      <div className="card__body">
        <h3 className="card__title">{product.name}</h3>
        {product.storage_place && <p className="card__place">{product.storage_place}</p>}
        <p className="card__meta">
          <span>{formatAmount(product)}</span>
          <span className="card__dot" aria-hidden="true">
            ·
          </span>
          <span className={`card__badge card__badge--${status}`}>{badgeTextOf(product)}</span>
        </p>
      </div>

      {selecting ? (
        <span className={`card__mark${selected ? ' is-on' : ''}`} aria-hidden="true" />
      ) : (
        <div className="card__actions">
          <button
            className="icon-btn"
            type="button"
            onClick={() => onAction(product, 'use')}
            aria-label={`Использовать «${product.name}»`}
          >
            <UtensilsIcon />
          </button>
          <button
            className="icon-btn icon-btn--danger"
            type="button"
            onClick={() => onAction(product, 'delete')}
            aria-label={`Удалить «${product.name}»`}
          >
            <TrashIcon />
          </button>
        </div>
      )}
    </article>
  )
}
