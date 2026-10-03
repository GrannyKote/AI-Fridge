import { useEffect, useMemo, useRef } from 'react'
import { displayProductName, statusOf } from '../lib/pantry.js'
import { ClockIcon, WarningIcon } from './icons.jsx'
import '../styles/dialog.css'

const GROUPS = [
  { key: 'expired', title: 'Просрочено', icon: <WarningIcon /> },
  { key: 'soon', title: 'Скоро испортится', icon: <ClockIcon /> },
]

export function NotificationsDialog({ products = [], onClose, onGo, onViewed }) {
  const viewed = useRef(false)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  useEffect(() => {
    if (products.length > 0 && !viewed.current) {
      viewed.current = true
      onViewed?.()
    }
  }, [onViewed, products.length])

  const groups = useMemo(
    () =>
      GROUPS.map((group) => ({
        ...group,
        items: products.filter((product) => statusOf(product) === group.key),
      })).filter((group) => group.items.length > 0),
    [products],
  )

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Требуют внимания">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <h2 className="dialog__title">Требуют внимания</h2>

        <div className="notifications__panel">
          {groups.length === 0 ? (
            <p className="notifications__empty">Всё в порядке</p>
          ) : (
            groups.map((group) => (
              <section className={`notifications__group notifications__group--${group.key}`} key={group.key}>
                <h3 className="notifications__head">
                  {group.icon}
                  {group.title} · {group.items.length}
                </h3>
                <ul className="notifications__list">
                  {group.items.map((product) => (
                    <li className="notifications__item" key={product.id}>
                      {displayProductName(product.name)}
                    </li>
                  ))}
                </ul>
              </section>
            ))
          )}
        </div>

        <button className="btn btn--primary" type="button" onClick={onGo}>
          Перейти
        </button>
      </div>
    </div>
  )
}
