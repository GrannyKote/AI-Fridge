import { TrashIcon, UtensilsIcon } from './icons.jsx'
import {
  badgeTextOf,
  categoryView,
  displayProductName,
  formatAmount,
  formatPrice,
  statusOf,
} from '../lib/pantry.js'

export function ProductCard({
  product,
  selected = false,
  actionsDisabled = false,
  onToggleSelect,
  onAction,
  onEdit,
}) {
  const status = statusOf(product)
  const name = displayProductName(product.name)
  const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)
  const subtitle = [product.storage_place, formatPrice(product.price)].filter(Boolean).join(' · ')

  return (
    <article
      className={`card${status === 'expired' ? ' card--expired' : ''}${selected ? ' card--selected' : ''}`}
    >
      <button
        className={`card__thumb card__thumb--${tone}${selected ? ' is-selected' : ''}`}
        type="button"
        onClick={() => onToggleSelect?.(product)}
        aria-label={selected ? `Снять выбор «${name}»` : `Выбрать «${name}»`}
        aria-pressed={selected}
      >
        {emoji}
      </button>

      <div className="card__body">
        <button
          className="card__title card__title-btn"
          type="button"
          disabled={actionsDisabled || !onEdit}
          onClick={() => onEdit?.(product)}
          aria-label={`Редактировать «${name}»`}
        >
          {name}
        </button>
        {subtitle && <p className="card__place">{subtitle}</p>}
        <p className="card__meta">
          <span>{formatAmount(product)}</span>
          <span className="card__dot" aria-hidden="true">
            ·
          </span>
          <span className={`card__badge card__badge--${status}`}>{badgeTextOf(product)}</span>
        </p>
      </div>

      <div className="card__actions">
        <button
          className="icon-btn"
          type="button"
          disabled={actionsDisabled}
          onClick={() => onAction(product, 'use')}
          aria-label={`Использовать «${name}»`}
        >
          <UtensilsIcon />
        </button>
        <button
          className="icon-btn icon-btn--danger"
          type="button"
          disabled={actionsDisabled}
          onClick={() => onAction(product, 'delete')}
          aria-label={`Удалить «${name}»`}
        >
          <TrashIcon />
        </button>
      </div>
    </article>
  )
}
