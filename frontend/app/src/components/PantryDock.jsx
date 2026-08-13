import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { CartIcon, ChartIcon, FridgeIcon, LogoutIcon, PlusIcon, UserIcon } from './icons.jsx'

const TABS = [
  { key: 'pantry', title: 'Кладовая', icon: <FridgeIcon />, path: '/' },
  { key: 'forecast', title: 'Прогнозы', icon: <ChartIcon />, path: '/forecast' },
  { key: 'shopping', title: 'Покупки', icon: <CartIcon /> },
  { key: 'profile', title: 'Профиль', icon: <UserIcon /> },
]

export function PantryDock({ open, onClose, onSignOut, onAdd, onSelectTab }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  useEffect(() => {
    if (!open) {
      return undefined
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  function selectTab(tab) {
    if (!tab.path) {
      onSelectTab(tab.title)
      return
    }

    if (tab.path === pathname) {
      onClose()
      return
    }

    navigate(tab.path)
  }

  return (
    <>
      {open && (
        <button
          className="dock__backdrop"
          type="button"
          onClick={onClose}
          aria-label="Закрыть меню"
        />
      )}

      <div className={`dock${open ? ' dock--open' : ''}`}>
        <div className="dock__inner">
          {onAdd && (
            <button className="fab" type="button" onClick={onAdd} aria-label="Добавить продукт">
              <PlusIcon />
            </button>
          )}

          <div className="dock__panel" hidden={!open}>
            <div className="dock__account">
              <button className="dock__logout" type="button" onClick={onSignOut}>
                <LogoutIcon />
                Выйти
              </button>
            </div>

            <nav className="tabbar" aria-label="Основная навигация">
              {TABS.map((tab) => {
                const active = tab.path === pathname

                return (
                  <button
                    key={tab.key}
                    className={`tab${active ? ' is-active' : ''}`}
                    type="button"
                    onClick={() => selectTab(tab)}
                    aria-current={active ? 'page' : undefined}
                  >
                    {tab.icon}
                    <span>{tab.title}</span>
                  </button>
                )
              })}
            </nav>
          </div>
        </div>
      </div>
    </>
  )
}
