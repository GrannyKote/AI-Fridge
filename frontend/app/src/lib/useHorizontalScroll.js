import { useEffect, useRef } from 'react'

// Колесо мыши по умолчанию прокручивает страницу, а не горизонтальную ленту,
// поэтому вертикальный жест над ней переводим в прокрутку вбок.
export function useHorizontalScroll() {
  const ref = useRef(null)

  useEffect(() => {
    const node = ref.current

    if (!node) {
      return undefined
    }

    function handleWheel(event) {
      const scrollable = node.scrollWidth - node.clientWidth

      if (scrollable <= 0 || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
        return
      }

      event.preventDefault()
      node.scrollLeft += event.deltaY
    }

    node.addEventListener('wheel', handleWheel, { passive: false })
    return () => node.removeEventListener('wheel', handleWheel)
  }, [])

  return ref
}
