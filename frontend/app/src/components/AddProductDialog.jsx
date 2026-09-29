import { useEffect, useRef, useState } from 'react'
import { pantryApi, receiptApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { dateFromIso, expiryDate, localDate, quantityForUnit } from '../lib/pantry.js'
import { DateField } from './DateField.jsx'
import { FormAlert } from './FormAlert.jsx'
import { SuggestInput } from './SuggestInput.jsx'
import {
  ArrowLeftIcon,
  CabinetIcon,
  CameraIcon,
  CanIcon,
  HouseIcon,
  IceIcon,
  MicIcon,
  PencilIcon,
  SnowflakeIcon,
  SpiceIcon,
} from './icons.jsx'
import '../styles/dialog.css'

const EMPTY_FORM = {
  name: '',
  productId: null,
  category: '',
  unitId: '',
  quantity: '1',
  purchasedAt: today(),
  bestBefore: '',
  placeId: '',
  rawLine: '',
}

const METHODS = [
  { key: 'receipt', title: 'Чек', icon: <CameraIcon /> },
  { key: 'manual', title: 'Вручную', icon: <PencilIcon /> },
  { key: 'voice', title: 'Голос', icon: <MicIcon /> },
]

const PLACE_ICONS = {
  Холодильник: <SnowflakeIcon />,
  Морозилка: <IceIcon />,
  Бакалея: <HouseIcon />,
  Шкаф: <CabinetIcon />,
  Специи: <SpiceIcon />,
  Консервы: <CanIcon />,
}

const PLACE_BY_NAME = {
  'Фарш говяжий': 'Морозилка',
  'Куриное филе': 'Морозилка',
}

const PLACE_BY_CATEGORY = {
  Молочные: 'Холодильник',
  Яйца: 'Холодильник',
  'Мясо и рыба': 'Холодильник',
  'Хлеб и выпечка': 'Шкаф',
  'Крупы и макароны': 'Бакалея',
  'Соусы и специи': 'Специи',
}

function today() {
  return localDate()
}

function matchPercent(score) {
  const value = Number(score)
  if (!Number.isFinite(value) || value < 0) {
    return ''
  }
  return `${Math.round(value * 100)}%`
}

function placeChoices(places, storage) {
  if (places.some((place) => place.name === storage)) {
    return places
  }
  return [{ id: storage, name: storage }, ...places]
}

function placeIdOf(places, name, category) {
  const wanted = PLACE_BY_NAME[name] || PLACE_BY_CATEGORY[category] || 'Шкаф'
  return String(places.find((place) => place.name === wanted)?.id ?? places[0]?.id ?? '')
}

function draftDate(item) {
  if (item.best_before) {
    return item.best_before
  }
  if (Number.isInteger(item.shelf_life_days) && item.shelf_life_days > 0) {
    return expiryDate(item.shelf_life_days)
  }
  return ''
}

export function AddProductDialog({ groupId, categories, onClose, onCreated, onBatchSaved }) {
  const { user } = useAuth()
  const [form, setForm] = useState(EMPTY_FORM)
  const [method, setMethod] = useState('receipt')
  const [units, setUnits] = useState([])
  const [places, setPlaces] = useState([])
  const [nameSuggestions, setNameSuggestions] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)
  const [saving, setSaving] = useState(false)
  const [placeTouched, setPlaceTouched] = useState(false)
  const [receiptDrafts, setReceiptDrafts] = useState([])
  const [voiceDrafts, setVoiceDrafts] = useState([])
  const [receiptSkipped, setReceiptSkipped] = useState([])
  const [voiceSkipped, setVoiceSkipped] = useState([])
  const captureKey = method === 'voice' ? 'voice' : 'receipt'
  const drafts = captureKey === 'voice' ? voiceDrafts : receiptDrafts
  const skipped = captureKey === 'voice' ? voiceSkipped : receiptSkipped
  const setDrafts = captureKey === 'voice' ? setVoiceDrafts : setReceiptDrafts
  const [extraCategories, setExtraCategories] = useState([])
  const [categoryOffer, setCategoryOffer] = useState(false)
  const [newCategory, setNewCategory] = useState('')
  const [recording, setRecording] = useState(false)
  const cameraRef = useRef(null)
  const libraryRef = useRef(null)
  const audioRef = useRef(null)
  const kindRef = useRef('receipt')
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const discardRef = useRef(false)
  const suggestedBefore = useRef('')
  const openedFrom = useRef(null)
  const categoryTouched = useRef(false)

  useEffect(() => {
    let cancelled = false

    Promise.all([pantryApi.units(), pantryApi.places()])
      .then(([unitList, placeList]) => {
        if (cancelled) {
          return
        }

        setUnits(unitList)
        setPlaces(placeList)
        setForm((current) => ({
          ...current,
          unitId: current.unitId || String(unitList.find((unit) => unit.name === 'шт')?.id ?? ''),
          placeId: current.placeId || placeIdOf(placeList, current.name, current.category),
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

    if (method !== 'manual' || query.length < 1) {
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
  }, [form.name, method])

  useEffect(() => {
    if (method !== 'manual') {
      return undefined
    }

    const query = form.name.trim()
    if (!query) {
      setForm((current) => {
        if (current.bestBefore && current.bestBefore !== suggestedBefore.current) {
          return current
        }
        suggestedBefore.current = ''
        return current.bestBefore ? { ...current, bestBefore: '' } : current
      })
      return undefined
    }

    let cancelled = false
    const timer = setTimeout(async () => {
      let nextDate = ''
      try {
        const found = await pantryApi.shelfLife(query)
        nextDate = found.shelf_life_days
      } catch {
        nextDate = ''
      }
      if (cancelled) {
        return
      }
      setForm((current) => {
        if (current.name.trim().toLowerCase() !== query.toLowerCase()) {
          return current
        }
        if (current.bestBefore && current.bestBefore !== suggestedBefore.current) {
          return current
        }
        const fixedDate = nextDate ? expiryDate(nextDate, dateFromIso(current.purchasedAt)) : ''
        suggestedBefore.current = fixedDate
        if (current.bestBefore === fixedDate) {
          return current
        }
        return { ...current, bestBefore: fixedDate }
      })
      if (nextDate) {
        clearError('bestBefore')
      }
    }, 250)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [form.name, form.purchasedAt, method])

  useEffect(() => {
    if (method !== 'manual') {
      return undefined
    }

    const query = form.name.trim()
    if (!query) {
      setCategoryOffer(false)
      return undefined
    }

    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const found = await pantryApi.searchProducts(query)
        if (cancelled) {
          return
        }
        const exact = found.find((product) => product.name.toLowerCase() === query.toLowerCase())
        if (exact?.category) {
          setCategoryOffer(false)
          if (!categoryTouched.current) {
            setForm((current) => {
              if (current.name.trim().toLowerCase() !== query.toLowerCase() || current.category === exact.category) {
                return current
              }
              return { ...current, category: exact.category }
            })
            clearError('category')
          }
          return
        }
        if (!categoryTouched.current) {
          setForm((current) =>
            current.category && current.name.trim().toLowerCase() === query.toLowerCase()
              ? { ...current, category: '' }
              : current,
          )
          setCategoryOffer(true)
        }
      } catch {
        if (!cancelled) {
          setCategoryOffer(false)
        }
      }
    }, 250)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [form.name, method])

  function update(patch) {
    setForm((current) => {
      const next = { ...current, ...patch }

      if (!placeTouched && places.length > 0 && ('name' in patch || 'category' in patch)) {
        next.placeId = placeIdOf(places, next.name.trim(), next.category)
      }

      return next
    })
  }

  function clearError(field) {
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  function releaseMic() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  function cancelVoice() {
    discardRef.current = true
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
      return
    }
    discardRef.current = false
    releaseMic()
    setRecording(false)
  }

  useEffect(() => {
    return () => {
      discardRef.current = true
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop()
      }
      releaseMic()
    }
  }, [])

  function pickFile(input) {
    if (!input) {
      return
    }
    input.value = ''
    input.click()
  }

  function openPhoto(fromLibrary) {
    setMethod('receipt')
    kindRef.current = 'receipt'
    setFormError('')
    pickFile(fromLibrary ? libraryRef.current : cameraRef.current)
  }

  function openAudioFile() {
    setMethod('voice')
    kindRef.current = 'voice'
    setFormError('')
    pickFile(audioRef.current)
  }

  async function startVoice() {
    setMethod('voice')
    kindRef.current = 'voice'
    setFormError('')
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      openAudioFile()
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream
      const mimeType = ['audio/mp4', 'audio/webm', 'audio/ogg'].find((type) =>
        MediaRecorder.isTypeSupported(type),
      )
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }
      recorder.onstop = () => {
        const discard = discardRef.current
        discardRef.current = false
        const type = recorder.mimeType || 'audio/mp4'
        const blob = new Blob(chunksRef.current, { type })
        releaseMic()
        setRecording(false)
        if (discard || blob.size === 0) {
          return
        }
        const ext = type.includes('webm') ? 'webm' : type.includes('ogg') ? 'ogg' : 'm4a'
        submitFile(new File([blob], `voice.${ext}`, { type }), 'voice')
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      releaseMic()
      setRecording(false)
      setFormError('Микрофон недоступен. Загрузите аудиофайл.')
    }
  }

  function stopVoice() {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
  }

  async function submitFile(file, kind) {
    setPending(true)
    setFormError('')
    try {
      const result = await receiptApi.recognize(groupId, file, kind)
      const items = result.items ?? []
      const missed = result.skipped ?? []
      const writeDrafts = kind === 'voice' ? setVoiceDrafts : setReceiptDrafts
      const writeSkipped = kind === 'voice' ? setVoiceSkipped : setReceiptSkipped
      writeDrafts(
        items.map((item) => ({
          ...item,
          originName: item.name,
          originDays: item.shelf_life_days,
          best_before:
            item.best_before ||
            (Number.isInteger(item.shelf_life_days) && item.shelf_life_days > 0
              ? expiryDate(item.shelf_life_days)
              : ''),
        })),
      )
      writeSkipped(missed)
      if (items.length === 0 && missed.length === 0) {
        setFormError('На записи не нашлось продуктов')
      }
    } catch (error) {
      const writeDrafts = kind === 'voice' ? setVoiceDrafts : setReceiptDrafts
      const writeSkipped = kind === 'voice' ? setVoiceSkipped : setReceiptSkipped
      writeDrafts([])
      writeSkipped([])
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  function openManual(next) {
    suggestedBefore.current = ''
    setPlaceTouched(true)
    setMethod('manual')
    setFormError('')
    setErrors({})
    setForm({
      ...EMPTY_FORM,
      purchasedAt: today(),
      ...next,
    })
  }

  function draftJob(item) {
    const name = String(item.name ?? '').trim()
    const unit = units.find((entry) => entry.name === item.unit)
    const place = places.find((entry) => entry.name === (item.storage || 'Шкаф'))
    const quantity = Number(String(item.quantity ?? '').replace(',', '.'))
    const bestBefore = draftDate(item)
    if (!name || !item.category || !unit || !place || !(quantity > 0) || !bestBefore) {
      return null
    }
    return { item: { ...item, name }, unit, place, quantity, bestBefore }
  }

  async function writeDraft(job) {
    const days = job.item.shelf_life_days
    if (Number.isInteger(days) && days > 0) {
      await rememberRow(job.item)
    }
    return pantryApi.addProduct(groupId, {
      name: job.item.name,
      category: job.item.category,
      unit_id: Number(job.unit.id),
      quantity: job.quantity,
      best_before: job.bestBefore,
      purchased_on: today(),
      storage_place_id: Number(job.place.id),
      user_id: user?.id,
    })
  }

  async function addAll() {
    const stay = []
    const jobs = []

    for (const item of drafts) {
      const job = draftJob(item)
      if (job) {
        jobs.push(job)
      } else {
        stay.push(item)
      }
    }

    if (jobs.length === 0) {
      setFormError('Нет строк со сроком и местом, которые можно записать сразу')
      return
    }

    setPending(true)
    setSaving(true)
    setFormError('')
    const saved = []
    const failed = []

    try {
      for (const job of jobs) {
        try {
          saved.push(await writeDraft(job))
        } catch (error) {
          failed.push(job.item)
          setFormError(error.message)
          break
        }
      }
    } finally {
      setSaving(false)
      setPending(false)
    }

    const left = [...failed, ...stay]
    setDrafts(left)
    if (saved.length > 0) {
      onBatchSaved(saved, left.length === 0 && skipped.length === 0)
    }
  }

  async function rememberRow(item) {
    const name = item.name.trim()
    const days = item.shelf_life_days
    if (!name || !Number.isInteger(days) || days <= 0) {
      throw new Error('Укажите имя и срок в днях')
    }
    if (name === item.originName && days === item.originDays) {
      return
    }
    await pantryApi.rememberShelfLife(name, days)
  }

  async function saveDraft(index) {
    const job = draftJob(drafts[index])
    if (!job) {
      setFormError('Укажите количество, срок и место')
      return
    }

    setPending(true)
    setSaving(true)
    setFormError('')
    try {
      const created = await writeDraft(job)
      const left = drafts.filter((_, at) => at !== index)
      setDrafts(left)
      onBatchSaved([created], left.length === 0 && skipped.length === 0)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setSaving(false)
      setPending(false)
    }
  }

  function acceptCategory(name) {
    const trimmed = name.trim()
    if (!trimmed) {
      return
    }
    const known = [...categories, ...extraCategories].find(
      (item) => item.name.toLowerCase() === trimmed.toLowerCase(),
    )
    const value = known ? known.name : trimmed
    if (!known) {
      setExtraCategories((current) => [...current, { id: value, name: value }])
    }
    categoryTouched.current = true
    setCategoryOffer(false)
    setNewCategory('')
    update({ category: value })
    clearError('category')
  }

  function takeSkipped(line) {
    openedFrom.current = method === 'voice' ? 'voice' : 'receipt'
    const unit = units.find((entry) => entry.name === 'шт')
    openManual({
      name: line,
      rawLine: line,
      quantity: '1',
      unitId: unit ? String(unit.id) : '',
      placeId: placeIdOf(places, '', ''),
    })
  }

  function onCapture(event) {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    submitFile(file, kindRef.current)
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
      bestBefore: form.bestBefore ? '' : 'Укажите срок годности',
      placeId: form.placeId ? '' : 'Выберите место хранения',
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
      if (form.rawLine.trim()) {
        const unit = units.find((entry) => String(entry.id) === String(form.unitId))
        await receiptApi.saveLabel(groupId, {
          raw_line: form.rawLine,
          name: form.name.trim(),
          quantity: Number(form.quantity.replace(',', '.')),
          unit: unit.name,
          category: form.category,
        })
      }
      const created = await pantryApi.addProduct(groupId, {
        name: form.name.trim(),
        category: form.category,
        unit_id: Number(form.unitId),
        quantity: Number(form.quantity.replace(',', '.')),
        best_before: form.bestBefore,
        purchased_on: form.purchasedAt || today(),
        storage_place_id: Number(form.placeId),
        product_id: form.productId,
        user_id: user?.id,
      })
      const back = openedFrom.current
      if (!back) {
        onCreated(created)
        return
      }
      openedFrom.current = null
      const raw = form.rawLine
      const writeSkipped = back === 'voice' ? setVoiceSkipped : setReceiptSkipped
      writeSkipped((current) => current.filter((row) => row.line !== raw))
      setMethod(back)
      setForm({ ...EMPTY_FORM, purchasedAt: today() })
      setErrors({})
      onBatchSaved([created], false)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog dialog--page" role="dialog" aria-modal="true" aria-labelledby="add-title">
      <div className="add">
        <header className="add__head">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
          <h2 className="add__title" id="add-title">
            Добавить продукт
          </h2>
        </header>

        <div className="method" role="tablist" aria-label="Способ добавления">
          {METHODS.map((item) => (
            <button
              key={item.key}
              className={`method__item${method === item.key ? ' is-active' : ''}`}
              type="button"
              role="tab"
              aria-selected={method === item.key}
              onClick={() => {
                if (item.key === method) {
                  return
                }
                if (recording) {
                  cancelVoice()
                }
                setMethod(item.key)
                setFormError('')
              }}
            >
              {item.icon}
              {item.title}
            </button>
          ))}
        </div>

        {method === 'receipt' && (
          <div className="capture">
            <button className="capture__btn" type="button" onClick={() => openPhoto(false)} disabled={pending}>
              Сфотографировать
            </button>
            <button className="capture__btn" type="button" onClick={() => openPhoto(true)} disabled={pending}>
              Из библиотеки
            </button>
          </div>
        )}

        {method === 'voice' && (
          <div className="capture">
            <button
              className={`capture__btn${recording ? ' is-recording' : ''}`}
              type="button"
              onClick={recording ? stopVoice : startVoice}
              disabled={pending}
            >
              {recording ? 'Стоп' : 'Записать'}
            </button>
            <button className="capture__btn" type="button" onClick={openAudioFile} disabled={pending || recording}>
              Загрузить запись
            </button>
          </div>
        )}

        <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={onCapture} />
        <input ref={libraryRef} type="file" accept="image/*" hidden onChange={onCapture} />
        <input ref={audioRef} type="file" accept="audio/*" hidden onChange={onCapture} />

        {method !== 'manual' && pending && !saving && <p className="drafts__hint">Разбираем запись...</p>}

        {method !== 'manual' && drafts.length > 0 && (
          <div className="drafts">
            <p className="drafts__hint">Что куплено, сколько, где хранить и до какой даты.</p>
            <button className="drafts__all" type="button" onClick={addAll} disabled={pending}>
              Добавить всё
            </button>
            <div className="drafts__head">
              <span>Куплено</span>
              <span>Сколько</span>
              <span>Хранение</span>
              <span>Срок</span>
            </div>
            {drafts.map((item, index) => (
              <div key={index} className="drafts__item">
                <div className="drafts__facts">
                  <div className="drafts__title">
                    <input
                      className="drafts__name"
                      aria-label={`Имя для строки ${index + 1}`}
                      value={item.name}
                      onChange={(event) => {
                        const name = event.target.value
                        setDrafts((current) =>
                          current.map((row, at) => (at === index ? { ...row, name } : row)),
                      )
                    }}
                  />
                    {matchPercent(item.score) && (
                      <span className="drafts__score">{matchPercent(item.score)}</span>
                    )}
                  </div>
                  <label className="drafts__qty">
                    <input
                      type="text"
                      inputMode="decimal"
                      aria-label={`Количество для ${item.name}`}
                      value={item.quantity ?? ''}
                      onChange={(event) => {
                        const quantity = event.target.value
                        setDrafts((current) =>
                          current.map((row, at) => (at === index ? { ...row, quantity } : row)),
                        )
                      }}
                    />
                    <span>{item.unit}</span>
                  </label>
                  <div className="drafts__place">
                    <select
                      className="drafts__place-select"
                      aria-label={`Место для ${item.name}`}
                      value={item.storage || 'Шкаф'}
                      onChange={(event) => {
                        const storage = event.target.value
                        setDrafts((current) =>
                          current.map((row, at) => (at === index ? { ...row, storage } : row)),
                        )
                      }}
                    >
                      {placeChoices(places, item.storage || 'Шкаф').map((place) => (
                        <option key={place.id} value={place.name}>
                          {place.name}
                        </option>
                      ))}
                    </select>
                    <span className="drafts__place-icon" aria-hidden="true">
                      {PLACE_ICONS[item.storage || 'Шкаф'] ?? <HouseIcon />}
                    </span>
                  </div>
                  <label className="drafts__days">
                    <input
                      type="number"
                      inputMode="numeric"
                      aria-label={`Срок в днях для ${item.name}`}
                      value={Number.isInteger(item.shelf_life_days) ? item.shelf_life_days : ''}
                      onChange={(event) => {
                        const raw = event.target.value
                        const parsed = raw === '' ? null : Number(raw)
                        const shelf_life_days = Number.isInteger(parsed) ? parsed : null
                        const best_before =
                          Number.isInteger(shelf_life_days) && shelf_life_days > 0
                            ? expiryDate(shelf_life_days)
                            : ''
                        setDrafts((current) =>
                          current.map((row, at) =>
                            at === index ? { ...row, shelf_life_days, best_before } : row,
                          ),
                        )
                      }}
                    />
                    <DateField
                      className="drafts__date"
                      ariaLabel={`Дата для ${item.name}`}
                      value={draftDate(item)}
                      onChange={(best_before) => {
                        setDrafts((current) =>
                          current.map((row, at) => (at === index ? { ...row, best_before } : row)),
                        )
                      }}
                    />
                  </label>
                </div>
                <div className="drafts__actions">
                  <button className="drafts__add" type="button" onClick={() => saveDraft(index)} disabled={pending}>
                    Добавить
                  </button>
                  <button
                    className="drafts__drop"
                    type="button"
                    onClick={() => setDrafts((current) => current.filter((_, at) => at !== index))}
                  >
                    Убрать
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {method !== 'manual' && skipped.length > 0 && (
          <div className="drafts">
            <p className="drafts__hint">Не попало в список. Нажмите строку, чтобы добавить её самим.</p>
            {skipped.map((row) => (
              <div key={row.line} className="drafts__miss-row">
                <button className="drafts__miss" type="button" onClick={() => takeSkipped(row.line)}>
                  <span>{row.line}</span>
                  {matchPercent(row.score) && (
                    <span className="drafts__score">{matchPercent(row.score)}</span>
                  )}
                </button>
                <button
                  className="drafts__drop"
                  type="button"
                  aria-label={`Удалить «${row.line}»`}
                  onClick={() => {
                    const writeSkipped = method === 'voice' ? setVoiceSkipped : setReceiptSkipped
                    writeSkipped((current) => current.filter((item) => item.line !== row.line))
                  }}
                >
                  Удалить
                </button>
              </div>
            ))}
          </div>
        )}

        {method !== 'manual' && <FormAlert>{formError}</FormAlert>}

        {method === 'manual' && (
        <form className="form add__form" onSubmit={handleSubmit} noValidate>
          <SuggestInput
              label="Название"
              value={form.name}
              onChange={(value) => {
                categoryTouched.current = false
                update({ name: value, productId: null })
                clearError('name')
              }}
              onPick={({ product }) => {
                categoryTouched.current = true
                setCategoryOffer(false)
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
            <label className="field__label" htmlFor="category">
              Категория
            </label>
            <div className="field__control">
              <select
                id="category"
                className="field__input field__select"
                value={form.category}
                onChange={(event) => {
                  categoryTouched.current = true
                  setCategoryOffer(false)
                  update({ category: event.target.value })
                  clearError('category')
                }}
              >
                <option value="">Выберите категорию</option>
                {[...categories, ...extraCategories.filter(
                  (extra) => !categories.some((category) => category.name.toLowerCase() === extra.name.toLowerCase()),
                )].map((category) => (
                  <option key={category.id} value={category.name}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            {errors.category && <p className="field__error">{errors.category}</p>}
            {categoryOffer && !form.category && (
              <div className="category-offer">
                <p>Такой категории нет. Создать её?</p>
                <input
                  className="field__input"
                  value={newCategory}
                  placeholder="Название категории"
                  onChange={(event) => setNewCategory(event.target.value)}
                />
                <button className="btn btn--ghost" type="button" onClick={() => acceptCategory(newCategory)}>
                  Создать
                </button>
              </div>
            )}
          </div>

          <div className="dialog__row">
            <div className={`field${errors.quantity ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="quantity">
                Количество
              </label>
              <div className="field__control">
                <input
                  id="quantity"
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
              <label className="field__label" htmlFor="unit">
                Единица
              </label>
              <div className="field__control">
                <select
                  id="unit"
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

          <div className="dialog__row">
            <div className="field">
              <label className="field__label" htmlFor="purchased-at">
                Дата покупки
              </label>
              <div className="field__control">
                <DateField
                  id="purchased-at"
                  className="field__input"
                  ariaLabel="Дата покупки"
                  value={form.purchasedAt}
                  onChange={(purchasedAt) => update({ purchasedAt })}
                />
              </div>
            </div>

            <div className={`field${errors.bestBefore ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="best-before">
                Срок годности
              </label>
              <div className="field__control">
                <DateField
                  id="best-before"
                  className="field__input"
                  ariaLabel="Срок годности"
                  value={form.bestBefore}
                  onChange={(bestBefore) => {
                    update({ bestBefore })
                    clearError('bestBefore')
                  }}
                />
              </div>
              {errors.bestBefore && <p className="field__error">{errors.bestBefore}</p>}
            </div>
          </div>

          <fieldset className={`places${errors.placeId ? ' field--invalid' : ''}`}>
            <legend className="field__label">Хранение</legend>
            <div className="places__grid">
              {places.map((place) => (
                <button
                  key={place.id}
                  className={`place${String(place.id) === String(form.placeId) ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => {
                    setPlaceTouched(true)
                    update({ placeId: String(place.id) })
                    clearError('placeId')
                  }}
                >
                  <span className="place__icon" aria-hidden="true">
                    {PLACE_ICONS[place.name] ?? <HouseIcon />}
                  </span>
                  {place.name}
                </button>
              ))}
            </div>
            {errors.placeId && <p className="field__error">{errors.placeId}</p>}
          </fieldset>

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Сохраняем...' : 'Сохранить'}
          </button>
        </form>
        )}
      </div>
    </div>
  )
}
