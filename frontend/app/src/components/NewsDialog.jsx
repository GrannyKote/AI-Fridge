import { useEffect } from 'react'
import '../styles/dialog.css'

export function NewsDialog({ onClose }) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Новости">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <h2 className="dialog__title">Новости</h2>

        <div className="notifications__panel" />
      </div>
    </div>
  )
}
