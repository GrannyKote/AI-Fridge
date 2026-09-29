// Единственный источник версии в интерфейсе: номер берётся из package.json при сборке,
// «MVP» — метка текущей стадии продукта.
export const APP_VERSION = `MVP ${import.meta.env.VITE_APP_VERSION}`
