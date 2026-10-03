import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { categoryView, displayProductName, formatAmount } from '../lib/pantry.js'
import { FormAlert } from './FormAlert.jsx'
import { WASTE_REASONS } from '../lib/wasteReasons.js'
import '../styles/dialog.css'

export function BulkWasteDialog({ groupId, products, onClose, onDone }) {
  const [reason, setReason] = useState('spoiled')
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  const spoiled = reason === 'spoiled'

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setPending(true)

    try {
      for (const product of products) {
        const remaining = Number(product.remaining ?? product.quantity)
        await pantryApi.wasteProduct(groupId, product.id, {
          reason,
          quantity: spoiled ? remaining : null,
        })
      }
      onDone(products.length, reason)
    } catch (wasteError) {
      setFormError(wasteError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Списать выбранное">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <form className="form writeoff" onSubmit={handleSubmit} noValidate>
          <h2 className="dialog__title">Списать выбранное</h2>

          <ul className="bulk-consume__list">
            {products.map((product) => {
              const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)
              const name = displayProductName(product.name)

              return (
                <li className="bulk-consume__row" key={product.id}>
                  <div className={`card__thumb card__thumb--${tone}`} aria-hidden="true">
                    {emoji}
                  </div>
                  <div className="bulk-consume__body">
                    <p className="bulk-consume__name">{name}</p>
                    <p className="writeoff__stock">Остаток: {formatAmount(product)}</p>
                  </div>
                </li>
              )
            })}
          </ul>

          <fieldset className="radios">
            <legend className="writeoff__label">Причина списания</legend>

            {WASTE_REASONS.map((option) => (
              <label className="radio__option" key={option.value}>
                <input
                  className="radio__input"
                  type="radio"
                  name="bulk-waste-reason"
                  value={option.value}
                  checked={reason === option.value}
                  onChange={() => setReason(option.value)}
                />
                <span>{option.title}</span>
              </label>
            ))}
          </fieldset>

          {spoiled ? (
            <p className="writeoff__note">Будут списаны все остатки перечисленных продуктов.</p>
          ) : (
            <p className="writeoff__note">
              Записи скроются из кладовой, количество списывать не нужно.
            </p>
          )}

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Списываем...' : 'Списать все'}
          </button>
        </form>
      </div>
    </div>
  )
}
