import { useEffect, useState } from 'react'
import { BellIcon, WarningIcon } from './icons.jsx'
import '../styles/dialog.css'
import '../styles/forecast.css'

const TABS = [
  { key: 'expiring', title: 'Скоро испортится', icon: <WarningIcon /> },
  { key: 'news', title: 'Новости', icon: <BellIcon /> },
]

export function NotificationsDialog({ onClose }) {
  const [tab, setTab] = useState('expiring')

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
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Уведомления">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <h2 className="dialog__title">Уведомления</h2>

        <div className="segmented" role="tablist" aria-label="Тип уведомлений">
          {TABS.map((item) => (
            <button
              key={item.key}
              className={`segmented__item${tab === item.key ? ' is-active' : ''}`}
              type="button"
              role="tab"
              id={`notifications-tab-${item.key}`}
              aria-selected={tab === item.key}
              aria-controls={`notifications-panel-${item.key}`}
              onClick={() => setTab(item.key)}
            >
              {item.icon}
              {item.title}
            </button>
          ))}
        </div>

        <div
          className="notifications__panel"
          role="tabpanel"
          id={`notifications-panel-${tab}`}
          aria-labelledby={`notifications-tab-${tab}`}
        />
      </div>
    </div>
  )
}
