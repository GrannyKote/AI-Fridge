import { existsSync, readdirSync, rmdirSync, unlinkSync } from 'node:fs'
import { join } from 'node:path'

// Рекурсивное удаление каталога на Windows срабатывает не всегда (по этой же
// причине не помогает build.emptyOutDir), поэтому файлы удаляются по одному:
// иначе бандлы прошлых сборок остаются в dist и попадают в кэш service worker.
function clean(directory) {
  if (!existsSync(directory)) {
    return
  }

  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name)

    if (entry.isDirectory()) {
      clean(path)
      rmdirSync(path)
    } else {
      unlinkSync(path)
    }
  }
}

clean('dist')
