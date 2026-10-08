import { categoryView, displayProductName, formatAmount, formatNumber, parseAmount } from '../lib/pantry.js'
import { MinusIcon, PlusIcon } from './icons.jsx'
import '../styles/pantry.css'

const RATIO_PRESETS = [
  { key: '25', label: '25%', ratio: 0.25 },
  { key: '50', label: '50%', ratio: 0.5 },
  { key: '75', label: '75%', ratio: 0.75 },
  { key: 'all', label: 'Всё', ratio: 1 },
]

function percentLabel(portion, available) {
  if (available <= 0) {
    return '0%'
  }

  const percent = (portion / available) * 100

  if (Math.abs(percent - 100) < 0.05) {
    return '100%'
  }

  if (Math.abs(percent - Math.round(percent)) < 0.05) {
    return `${Math.round(percent)}%`
  }

  return `${percent.toFixed(1)}%`
}

function presetsFor(available, unit) {
  if (unit !== 'шт' || available < 1) {
    return RATIO_PRESETS.map((preset) => ({
      ...preset,
      portion: shareOf(available, preset.ratio),
    }))
  }

  const one = 1
  const first = {
    key: '1',
    label: percentLabel(one, available),
    portion: one,
  }

  const rest = RATIO_PRESETS.map((preset) => ({
    ...preset,
    portion: shareOf(available, preset.ratio),
  })).filter((preset) => preset.portion > one)

  return [first, ...rest]
}

function shareOf(available, ratio) {
  // «Всё» — это ровно остаток, без округления дробной части.
  if (ratio === 1) {
    return available
  }

  const value = available * ratio

  if (Number.isInteger(available)) {
    return Math.round(value)
  }

  return Number(value.toFixed(2))
}

function sameAmount(raw, amount) {
  return Math.abs(parseAmount(raw) - amount) < 1e-9
}

function stepSize(available, unit) {
  if (unit === 'шт' || Number.isInteger(available)) {
    return 1
  }

  return available >= 10 ? 1 : 0.1
}

export function ProductHead({ product, available }) {
  const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)

  return (
    <div className="writeoff__product">
      <div className={`card__thumb card__thumb--${tone}`} aria-hidden="true">
        {emoji}
      </div>
      <div>
        <h3 className="writeoff__name">{displayProductName(product.name)}</h3>
        <p className="writeoff__stock">В наличии: {formatAmount({ ...product, remaining: available })}</p>
      </div>
    </div>
  )
}

export function QuantityPicker({
  product,
  available,
  value,
  onChange,
  label,
  error,
  showTrack = true,
}) {
  const amount = parseAmount(value)
  const safeAmount = Number.isFinite(amount) && amount > 0 ? Math.min(amount, available) : 0
  const step = stepSize(available, product.unit)
  const ratio = available > 0 ? (safeAmount / available) * 100 : 0
  const presets = presetsFor(available, product.unit)

  function setAmount(next) {
    const clamped = Math.min(Math.max(next, 0), available)
    onChange(clamped === 0 ? '' : formatNumber(clamped))
  }

  return (
    <div className="writeoff">
      <p className="writeoff__label">{label}</p>

      <div className="writeoff__presets">
        {presets.map((preset) => (
          <button
            key={preset.key}
            className={`preset${sameAmount(value, preset.portion) ? ' is-active' : ''}`}
            type="button"
            onClick={() => setAmount(preset.portion)}
          >
            <span>{preset.label}</span>
            <span className="preset__amount">
              {formatNumber(preset.portion)}
              {product.unit ? ` ${product.unit}` : ''}
            </span>
          </button>
        ))}
      </div>

      <div className={`writeoff__counter${error ? ' is-invalid' : ''}`}>
        <button
          className="stepper"
          type="button"
          onClick={() => setAmount(safeAmount - step)}
          aria-label="Уменьшить"
        >
          <MinusIcon />
        </button>

        <input
          className="writeoff__input"
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-label="Количество"
        />

        <button
          className="stepper"
          type="button"
          onClick={() => setAmount(safeAmount + step)}
          aria-label="Увеличить"
        >
          <PlusIcon />
        </button>

        {product.unit && <span className="writeoff__unit">{product.unit}</span>}
      </div>

      {showTrack && (
        <div className="writeoff__track" aria-hidden="true">
          <i className="writeoff__fill" style={{ width: `${ratio}%` }} />
        </div>
      )}

      {error && <p className="field__error">{error}</p>}
    </div>
  )
}
