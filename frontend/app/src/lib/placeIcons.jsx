import {
  CabinetIcon,
  CanIcon,
  HouseIcon,
  IceIcon,
  SnowflakeIcon,
  SpiceIcon,
} from '../components/icons.jsx'

export const PLACE_ICONS = {
  Холодильник: <SnowflakeIcon />,
  Морозилка: <IceIcon />,
  Бакалея: <HouseIcon />,
  Шкаф: <CabinetIcon />,
  Специи: <SpiceIcon />,
  Консервы: <CanIcon />,
}

export function placeIconFor(name) {
  return PLACE_ICONS[name] ?? <HouseIcon />
}
