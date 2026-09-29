import { useLocation, useNavigate } from 'react-router-dom'
import { APP_VERSION } from '../lib/appVersion.js'
import { CartIcon, ChartIcon, FridgeIcon, PlusIcon, UserIcon } from './icons.jsx'

const TABS = [
  { key: 'pantry', title: 'Кладовая', icon: <FridgeIcon />, path: '/' },
  { key: 'forecast', title: 'Прогнозы', icon: <ChartIcon />, path: '/forecast' },
  { key: 'shopping', title: 'Покупки', icon: <CartIcon />, path: '/shopping' },
  { key: 'settings', title: 'Настройки', icon: <UserIcon />, path: '/settings' },
]

export function PantryDock({ onAdd }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <div className="dock">
      <div className="dock__inner">
        {onAdd && (
          <button className="fab" type="button" onClick={onAdd} aria-label="Добавить продукт">
            <PlusIcon />
          </button>
        )}

        <div className="dock__panel">
          <nav className="tabbar" aria-label="Основная навигация">
            {TABS.map((tab) => {
              const active = tab.path === pathname

              return (
                <button
                  key={tab.key}
                  className={`tab${active ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => !active && navigate(tab.path)}
                  aria-current={active ? 'page' : undefined}
                >
                  {tab.icon}
                  <span>{tab.title}</span>
                </button>
              )
            })}
          </nav>

          <p className="dock__version">{APP_VERSION}</p>
        </div>
      </div>
    </div>
  )
}
