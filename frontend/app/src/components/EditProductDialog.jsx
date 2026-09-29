import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { quantityForUnit } from '../lib/pantry.js'
import { DateField } from './DateField.jsx'
import { FormAlert } from './FormAlert.jsx'
import {
  ArrowLeftIcon,
  CabinetIcon,
  CanIcon,
  HouseIcon,
  IceIcon,
  SnowflakeIcon,
  SpiceIcon,
} from './icons.jsx'
import '../styles/dialog.css'

const PLACE_ICONS = {
  Холодильник: <SnowflakeIcon />,
  Морозилка: <IceIcon />,
  Бакалея: <HouseIcon />,
  Шкаф: <CabinetIcon />,
  Специи: <SpiceIcon />,
  Консервы: <CanIcon />,
}

function amountText(value) {
  const number = Number(value)
  return Number.isFinite(number) ? String(number) : ''
}

export function EditProductDialog({ groupId, product, categories, places, onClose, onSaved }) {
  const [units, setUnits] = useState([])
  const [name, setName] = useState(product.name)
  const [category, setCategory] = useState(product.category ?? '')
  const [quantity, setQuantity] = useState(amountText(product.remaining))
  const [unitId, setUnitId] = useState('')
  const [placeId, setPlaceId] = useState(product.storage_place_id ? String(product.storage_place_id) : '')
  const [bestBefore, setBestBefore] = useState(product.best_before ?? '')
  const [purchasedOn, setPurchasedOn] = useState(product.purchased_on ?? '')
  const [error, setError] = useState('')
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
        const current = list.find((unit) => unit.name === product.unit)
        if (current) {
          setUnitId(String(current.id))
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
        }
      })
    return () => {
      cancelled = true
    }
  }, [product.unit])

  const categoryOptions = categories.some((item) => item.name === category)
    ? categories
    : category
      ? [{ id: 'current', name: category }, ...categories]
      : categories

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    const nextName = name.trim()
    const amount = Number(quantity.replace(',', '.'))
    if (!nextName || !category || !unitId || !placeId || !(amount > 0) || !bestBefore) {
      setError('Заполните количество, единицу, место, тип и срок')
      return
    }

    setPending(true)
    try {
      const saved = await pantryApi.updateProduct(groupId, product.id, {
        name: nextName,
        category,
        unit_id: Number(unitId),
        quantity: amount,
        best_before: bestBefore,
        purchased_on: purchasedOn || null,
        storage_place_id: Number(placeId),
      })
      onSaved(saved)
    } catch (err) {
      setError(err.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div
      className="dialog dialog--page"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="add">
        <header className="add__head">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
          <h2 className="add__title" id="edit-title">
            {product.name}
          </h2>
        </header>

        <form className="form add__form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label className="field__label" htmlFor="edit-name">
              Название
            </label>
            <input
              id="edit-name"
              className="field__input"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>

          <div className="dialog__row">
            <div className="field">
              <label className="field__label" htmlFor="edit-quantity">
                Количество
              </label>
              <input
                id="edit-quantity"
                className="field__input"
                type="text"
                inputMode="decimal"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="edit-unit">
                Единица
              </label>
              <select
                id="edit-unit"
                className="field__input field__select"
                value={unitId}
                onChange={(event) => {
                  const nextId = event.target.value
                  setUnitId(nextId)
                  const amount = quantityForUnit(units.find((unit) => String(unit.id) === nextId)?.name)
                  if (amount) setQuantity(amount)
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
          </div>

          <div className="field">
            <label className="field__label" htmlFor="edit-category">
              Тип
            </label>
            <select
              id="edit-category"
              className="field__input field__select"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="">Выберите тип</option>
              {categoryOptions.map((item) => (
                <option key={item.id} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label className="field__label" htmlFor="edit-bought">
              Дата покупки
            </label>
            <DateField
              id="edit-bought"
              className="field__input"
              ariaLabel="Дата покупки"
              value={purchasedOn}
              onChange={setPurchasedOn}
            />
          </div>

          <div className="field">
            <label className="field__label" htmlFor="edit-date">
              Срок годности
            </label>
            <DateField
              id="edit-date"
              className="field__input"
              ariaLabel="Срок годности"
              value={bestBefore}
              onChange={setBestBefore}
            />
          </div>

          <fieldset className="places">
            <legend className="field__label">Место хранения</legend>
            <div className="places__grid">
              {places.map((place) => (
                <button
                  key={place.id}
                  className={`place${String(place.id) === placeId ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => setPlaceId(String(place.id))}
                >
                  <span className="place__icon" aria-hidden="true">
                    {PLACE_ICONS[place.name] ?? <HouseIcon />}
                  </span>
                  {place.name}
                </button>
              ))}
            </div>
          </fieldset>

          <FormAlert>{error}</FormAlert>
          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Сохраняем...' : 'Сохранить'}
          </button>
        </form>
      </div>
    </div>
  )
}
