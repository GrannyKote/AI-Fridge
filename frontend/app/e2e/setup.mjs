import { execFileSync, spawn } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { once } from 'node:events'
import { createServer } from 'node:net'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'

async function waitForServer(server, url) {
  const deadline = Date.now() + 15000
  while (Date.now() < deadline && server.exitCode === null && server.signalCode === null) {
    const response = await fetch(url, { signal: AbortSignal.timeout(1000) }).catch(() => null)
    if (response?.ok) {
      await response.body?.cancel()
      return
    }
    await response?.body?.cancel()
    await delay(100)
  }
  throw new Error(`Не удалось запустить тестовый сервер ${url}`)
}

async function checkPort(url) {
  const { hostname, port } = new URL(url)
  const probe = createServer().listen(Number(port), hostname)
  await once(probe, 'listening')
  await new Promise((resolve) => probe.close(resolve))
}

export default async function setup(config) {
  const schema = `e2e_${randomUUID().replaceAll('-', '')}`
  const app = fileURLToPath(new URL('../', import.meta.url))
  const cwd = fileURLToPath(new URL('../../../backend/', import.meta.url))
  const python = process.env.PLAYWRIGHT_PYTHON ??
    (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python')
  const env = { ...process.env, DB_SCHEMA: schema, PYTHONIOENCODING: 'utf-8' }
  const auditOutput = process.env.PLAYWRIGHT_EXPERIMENT_AUDIT
  const auditScript = fileURLToPath(new URL('../../../research/offline-mvp/db-audit.py', import.meta.url))
  const apiPort = Number(process.env.PLAYWRIGHT_API_PORT ?? 18000)
  const api = 'http://127.0.0.1:' + apiPort
  const baseURL = config.projects[0].use.baseURL
  await Promise.all([checkPort(api), checkPort(baseURL)])
  const servers = []
  async function start(command, args, options, url, stopThroughStdin = false) {
    const server = spawn(command, args, {
      ...options, stdio: [stopThroughStdin ? 'pipe' : 'ignore', 'inherit', 'inherit'],
      windowsHide: true,
    })
    await once(server, 'spawn')
    servers.push({ server, stopThroughStdin })
    await waitForServer(server, url)
  }
  const run = (...args) => execFileSync(python, args, { cwd, env, stdio: 'inherit' })
  const schemaCommand = (statement) => run('-c', [
    'from app.database import engine',
    'from app.config import settings',
    'with engine.begin() as connection:',
    '    schema = connection.dialect.identifier_preparer.quote_schema(settings.db_schema)',
    `    connection.exec_driver_sql(f"${statement}")`,
  ].join('\n'))
  const audit = (...args) => run('-c', 'import runpy, sys; sys.argv.pop(0); runpy.run_path(sys.argv[0])', auditScript, ...args)
  schemaCommand('CREATE SCHEMA {schema}')
  let auditInstalled = false
  const cleanup = async () => {
    await Promise.all(servers.map(async ({ server, stopThroughStdin }) => {
      if (server.exitCode !== null || server.signalCode !== null) return
      const exited = once(server, 'exit')
      if (stopThroughStdin) server.stdin.end()
      else server.kill()
      await exited
    }))
    try {
      if (auditInstalled) audit('export', auditOutput)
    } finally {
      schemaCommand('DROP SCHEMA {schema} CASCADE')
    }
  }

  try {
    run('-m', 'alembic', 'upgrade', 'head')
    run('seed_demo.py')
    if (auditOutput) {
      audit('install')
      auditInstalled = true
    }
    // Windows virtualenv Python can delegate to another process. EOF reaches the API directly.
    await start(python, ['-c', [
      'import sys, threading, uvicorn',
      'server = uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=' + apiPort + '))',
      'def stop_on_eof():',
      '    sys.stdin.read()',
      '    server.should_exit = True',
      'threading.Thread(target=stop_on_eof, daemon=True).start()',
      'server.run()',
    ].join('\n')], { cwd, env }, `${api}/api/health`, true)
    if (process.env.PLAYWRIGHT_DATA_MODE === 'offline-first') {
      const response = await fetch(`${api}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login: 'demo', password: 'demo123' }),
      })
      if (!response.ok) throw new Error('Не удалось получить профиль demo для Offline-first')
      const { id } = await response.json()
      process.env.PLAYWRIGHT_DEMO_ID = String(id)
    }
    const viteArgs = ['node_modules/vite/bin/vite.js']
    if (process.env.PLAYWRIGHT_FRONTEND === 'preview') viteArgs.push('preview')
    await start(process.execPath, [...viteArgs, '--host', '127.0.0.1',
      '--port', new URL(baseURL).port, '--strictPort'], {
      cwd: app,
      env: { ...process.env, VITE_API_PROXY: api, VITE_API_URL: '/api' },
    }, baseURL)
  } catch (error) {
    await cleanup()
    throw error
  }
  return cleanup
}


