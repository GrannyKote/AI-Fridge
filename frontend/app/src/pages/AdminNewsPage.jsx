import { useCallback, useEffect, useState } from 'react'
import { adminNewsApi } from '../api/client.js'
import { AdminNewsDialog } from '../components/AdminNewsDialog.jsx'
import { AdminNewsSeenDialog } from '../components/AdminNewsSeenDialog.jsx'
import { AdminShell } from '../components/AdminShell.jsx'
import { EyeIcon, TrashIcon } from '../components/icons.jsx'
import { useToast } from '../lib/useToast.js'
import '../styles/dialog.css'

export default function AdminNewsPage() {
  const [items, setItems] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [seenTarget, setSeenTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [toast, setToast] = useToast()

  const load = useCallback(async () => {
    setState('loading')
    try {
      setItems(await adminNewsApi.list())
      setError('')
      setState('ready')
    } catch (loadError) {
      setError(loadError.message)
      setState('error')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleDeleteConfirm() {
    if (!deleteTarget || deletingId) {
      return
    }

    setDeletingId(deleteTarget.id)
    try {
      await adminNewsApi.remove(deleteTarget.id)
      setItems((current) => current.filter((item) => item.id !== deleteTarget.id))
      if (openId === deleteTarget.id) {
        setOpenId(null)
      }
      setToast('Новость удалена')
      setDeleteTarget(null)
    } catch (deleteError) {
      setToast(deleteError.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <AdminShell
      title="Управление новостями"
      toast={toast}
      onAdd={() => {
        setOpenId(null)
        setCreateOpen(true)
      }}
    >
      {state === 'loading' && <p className="pantry__message">Загружаем новости...</p>}

      {state === 'error' && (
        <div className="pantry__message">
          <p>{error}</p>
          <button className="btn btn--ghost" type="button" onClick={load}>
            Повторить
          </button>
        </div>
      )}

      {state === 'ready' && items.length === 0 && (
        <p className="pantry__message">Пока нет новостей</p>
      )}

      {state === 'ready' && items.length > 0 && (
        <ul className="news__list admin-news__list">
          {items.map((item) => (
            <li className="admin-news__item" key={item.id}>
              <button
                className="admin-news__open"
                type="button"
                onClick={() => {
                  setCreateOpen(false)
                  setOpenId(item.id)
                }}
              >
                <span className="news__header">{item.header}</span>
              </button>
              <div className="admin-news__actions">
                <button
                  className="icon-btn"
                  type="button"
                  onClick={() => setSeenTarget(item)}
                  aria-label={`Кто прочитал «${item.header}»`}
                >
                  <EyeIcon />
                </button>
                <button
                  className="icon-btn icon-btn--danger"
                  type="button"
                  onClick={() => setDeleteTarget(item)}
                  disabled={deletingId === item.id}
                  aria-label={`Удалить «${item.header}»`}
                >
                  <TrashIcon />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {createOpen && (
        <AdminNewsDialog
          onClose={() => setCreateOpen(false)}
          onSaved={(saved) => {
            setItems((current) => [{ id: saved.id, header: saved.header }, ...current])
            setState('ready')
            setToast('Новость создана')
          }}
        />
      )}

      {openId && (
        <AdminNewsDialog
          newsId={openId}
          onClose={() => setOpenId(null)}
          onSaved={(saved) => {
            setItems((current) =>
              current.map((item) => (item.id === saved.id ? { ...item, header: saved.header } : item)),
            )
            setToast('Новость сохранена')
          }}
        />
      )}

      {seenTarget && (
        <AdminNewsSeenDialog
          newsId={seenTarget.id}
          header={seenTarget.header}
          onClose={() => setSeenTarget(null)}
        />
      )}

      {deleteTarget && (
        <div
          className="dialog"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="delete-news-title"
          aria-describedby="delete-news-text"
        >
          <button
            className="dialog__backdrop"
            type="button"
            onClick={() => !deletingId && setDeleteTarget(null)}
            aria-label="Закрыть"
          />

          <div className="dialog__sheet">
            <div className="dialog__grabber" aria-hidden="true" />

            <h2 className="dialog__title" id="delete-news-title">
              Удалить новость?
            </h2>
            <p className="dialog__subtitle" id="delete-news-text">
              «{deleteTarget.header}» исчезнет из списка у пользователей и администратора. Это действие
              нельзя отменить.
            </p>

            <div className="admin-news__confirm-actions">
              <button
                className="btn btn--ghost"
                type="button"
                onClick={() => setDeleteTarget(null)}
                disabled={Boolean(deletingId)}
              >
                Отмена
              </button>
              <button
                className="btn admin-news__delete"
                type="button"
                onClick={handleDeleteConfirm}
                disabled={Boolean(deletingId)}
              >
                {deletingId ? 'Удаляем...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
