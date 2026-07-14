import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const apiBase = 'http://127.0.0.1:8000/api/v1'
const webOrigin = 'http://127.0.0.1:5173'

export default async function globalSetup() {
  const bootstrap = await fetch(`${apiBase}/auth/bootstrap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'visual@example.de', password: 'playwright-visual-password', display_name: 'Dimitri' }),
  })
  if (!bootstrap.ok) throw new Error(`Playwright-Konto konnte nicht angelegt werden: ${bootstrap.status} ${await bootstrap.text()}`)
  const tokens = await bootstrap.json() as { access_token: string; refresh_token: string; token_type: string; expires_in: number }
  const authorization = { Authorization: `Bearer ${tokens.access_token}` }

  const sourcePath = resolve(dirname(fileURLToPath(import.meta.url)), '../../examples/sample-ride.tcx')
  const form = new FormData()
  form.set('file', new Blob([await readFile(sourcePath)], { type: 'application/xml' }), 'sample-ride.tcx')
  form.set('title', 'Morgenrunde am See')
  const imported = await fetch(`${apiBase}/activities`, { method: 'POST', headers: authorization, body: form })
  if (!imported.ok) throw new Error(`Beispielaktivität konnte nicht importiert werden: ${imported.status} ${await imported.text()}`)

  const storagePath = resolve(dirname(fileURLToPath(import.meta.url)), '.auth/user.json')
  await mkdir(dirname(storagePath), { recursive: true })
  await writeFile(storagePath, JSON.stringify({
    cookies: [],
    origins: [{ origin: webOrigin, localStorage: [{ name: 'avento.auth.tokens', value: JSON.stringify(tokens) }, { name: 'avento-color-mode', value: 'dark' }] }],
  }, null, 2))
}
