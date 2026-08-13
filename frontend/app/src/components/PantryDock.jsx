import { CartIcon, ChartIcon, FridgeIcon, LogoutIcon, PlusIcon, UserIcon } from './icons.jsx'

const TABS = [
  { key: 'pantry', title: 'Кладовая', icon: <FridgeIcon /> },
  { key: 'forecast', title: 'Прогнозы', icon: <ChartIcon /> },
  { key: 'shopping', title: 'Покупки', icon: <CartIcon /> },
  { key: 'profile', title: 'Профиль', icon: <UserIcon /> },
]

export function PantryDock({ open, onClose, onSignOut, onAdd, onSelectTab }) {
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
          <button className="fab" type="button" onClick={onAdd} aria-label="Добавить продукт">
            <PlusIcon />
          </button>

          <div className="dock__panel" hidden={!open}>
            <div className="dock__account">
              <button className="dock__logout" type="button" onClick={onSignOut}>
                <LogoutIcon />
                Выйти
              </button>
            </div>

            <nav className="tabbar" aria-label="Основная навигация">
              {TABS.map((tab, index) => (
                <button
                  key={tab.key}
                  className={`tab${index === 0 ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => (index === 0 ? onClose() : onSelectTab(tab.title))}
                  aria-current={index === 0 ? 'page' : undefined}
                >
                  {tab.icon}
                  <span>{tab.title}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>
      </div>
    </>
  )
}
