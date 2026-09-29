import { useEffect, useState } from 'react'
import { pantryApi, shoppingApi } from '../api/client.js'
import { quantityForUnit } from '../lib/pantry.js'
import { FormAlert } from './FormAlert.jsx'
import { SuggestInput } from './SuggestInput.jsx'
import { ArrowLeftIcon } from './icons.jsx'
import '../styles/dialog.css'

const EMPTY_FORM = {
  name: '',
  productId: null,
  category: '',
  unitId: '',
  quantity: '1',
}

export function AddPurchaseDialog({ groupId, categories, onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [units, setUnits] = useState([])
  const [nameSuggestions, setNameSuggestions] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let cancelled = false

    pantryApi
      .units()
      .then((list) => {
        if (cancelled) {
          return
        }

        setUnits(list)
        setForm((current) => ({
          ...current,
          unitId: current.unitId || String(list.find((unit) => unit.name === 'шт')?.id ?? ''),
        }))
      })
      .catch((error) => setFormError(error.message))

    return () => {
      cancelled = true
    }
  }, [])

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
    const query = form.name.trim()

    if (query.length < 1) {
      setNameSuggestions([])
      return undefined
    }

    const timer = setTimeout(async () => {
      try {
        const found = await pantryApi.searchProducts(query)
        setNameSuggestions(
          found.map((product) => ({
            key: product.id,
            label: product.name,
            meta: product.category ?? '',
            product,
          })),
        )
      } catch {
        setNameSuggestions([])
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [form.name])

  function update(patch) {
    setForm((current) => ({ ...current, ...patch }))
  }

  function clearError(field) {
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  function validate() {
    const quantity = Number(form.quantity.replace(',', '.'))

    return {
      name: form.name.trim() ? '' : 'Введите название',
      category: form.category ? '' : 'Выберите категорию',
      unitId: form.unitId ? '' : 'Выберите единицу',
      quantity:
        form.quantity.trim() === ''
          ? 'Введите количество'
          : Number.isFinite(quantity) && quantity > 0
            ? ''
            : 'Количество должно быть больше нуля',
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const nextErrors = validate()
    setErrors(nextErrors)

    if (Object.values(nextErrors).some(Boolean)) {
      return
    }

    setPending(true)
    try {
      const created = await shoppingApi.add(groupId, {
        name: form.name.trim(),
        category: form.category,
        unit_id: Number(form.unitId),
        quantity: Number(form.quantity.replace(',', '.')),
        product_id: form.productId,
      })
      onCreated(created)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div
      className="dialog dialog--page"
      role="dialog"
      aria-modal="true"
      aria-labelledby="buy-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="add">
        <header className="add__head">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
          <h2 className="add__title" id="buy-title">
            Добавить в список
          </h2>
        </header>

        <form className="form add__form" onSubmit={handleSubmit} noValidate>
          <SuggestInput
            label="Название"
            value={form.name}
            onChange={(value) => {
              update({ name: value, productId: null })
              clearError('name')
            }}
            onPick={({ product }) => {
              update({
                name: product.name,
                productId: product.id,
                category: product.category ?? '',
              })
              clearError('name')
              clearError('category')
            }}
            suggestions={nameSuggestions}
            error={errors.name}
            placeholder="Начните вводить..."
            autoFocus
          />

          <div className={`field${errors.category ? ' field--invalid' : ''}`}>
            <label className="field__label" htmlFor="buy-category">
              Категория
            </label>
            <div className="field__control">
              <select
                id="buy-category"
                className="field__input field__select"
                value={form.category}
                onChange={(event) => {
                  update({ category: event.target.value })
                  clearError('category')
                }}
              >
                <option value="">Выберите категорию</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.name}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            {errors.category && <p className="field__error">{errors.category}</p>}
          </div>

          <div className="dialog__row">
            <div className={`field${errors.quantity ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="buy-quantity">
                Количество
              </label>
              <div className="field__control">
                <input
                  id="buy-quantity"
                  className="field__input"
                  type="text"
                  inputMode="decimal"
                  value={form.quantity}
                  onChange={(event) => {
                    update({ quantity: event.target.value })
                    clearError('quantity')
                  }}
                />
              </div>
              {errors.quantity && <p className="field__error">{errors.quantity}</p>}
            </div>

            <div className={`field${errors.unitId ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="buy-unit">
                Единица
              </label>
              <div className="field__control">
                <select
                  id="buy-unit"
                  className="field__input field__select"
                  value={form.unitId}
                  onChange={(event) => {
                    const nextId = event.target.value
                    const amount = quantityForUnit(units.find((unit) => String(unit.id) === nextId)?.name)
                    update(amount ? { unitId: nextId, quantity: amount } : { unitId: nextId })
                    clearError('unitId')
                    if (amount) clearError('quantity')
                  }}
                >
                  <option value="">Выберите</option>
                  {units.map((unit) => (
                    <option key={unit.id} value={unit.id}>
                      {unit.name}
                    </option>
                  ))}
                </select>
              </div>
              {errors.unitId && <p className="field__error">{errors.unitId}</p>}
            </div>
          </div>

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Добавляем...' : 'Добавить'}
          </button>
        </form>
      </div>
    </div>
  )
}
