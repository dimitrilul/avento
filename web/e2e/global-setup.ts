import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { rides, tcxForRide } from './fixture-data'

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

  const importedActivities: Array<{ id: string; title: string }> = []
  for (const [index, ride] of rides.entries()) {
    const form = new FormData()
    form.set('file', new Blob([tcxForRide(ride)], { type: 'application/xml' }), `visual-ride-${index + 1}.tcx`)
    form.set('title', ride.title)
    form.set('type', ride.type)
    if (ride.notes) form.set('notes', ride.notes)
    const imported = await fetch(`${apiBase}/activities`, { method: 'POST', headers: authorization, body: form })
    if (!imported.ok) throw new Error(`Beispielaktivität ${index + 1} konnte nicht importiert werden: ${imported.status} ${await imported.text()}`)
    const activity = await imported.json() as { id: string; title: string }
    importedActivities.push(activity)
    if (ride.hydrationMl != null) {
      const update = await fetch(`${apiBase}/activities/${activity.id}`, { method: 'PATCH', headers: { ...authorization, 'Content-Type': 'application/json' }, body: JSON.stringify({ hydration_ml: ride.hydrationMl }) })
      if (!update.ok) throw new Error(`Trinkmenge konnte nicht gesetzt werden: ${update.status}`)
    }
  }

  const profileResponse = await fetch(`${apiBase}/profile`, { headers: authorization })
  if (!profileResponse.ok) throw new Error(`Playwright-Profil konnte nicht geladen werden: ${profileResponse.status}`)
  const profile = await profileResponse.json() as { id: string }
  const mcpClient = await fetch(`${apiBase}/mcp/clients`, {
    method: 'POST',
    headers: { ...authorization, 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'Trainingsanalyse lokal', owner_user_id: profile.id, scopes: ['activities:read', 'statistics:read'] }),
  })
  if (!mcpClient.ok) throw new Error(`MCP-Testclient konnte nicht angelegt werden: ${mcpClient.status} ${await mcpClient.text()}`)

  const invitation = await fetch(`${apiBase}/auth/invitations`, { method: 'POST', headers: { ...authorization, 'Content-Type': 'application/json' }, body: '{}' })
  if (!invitation.ok) throw new Error(`Testeinladung konnte nicht erstellt werden: ${invitation.status}`)
  const invitationData = await invitation.json() as { token: string }
  const registration = await fetch(`${apiBase}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'leer@example.de', password: 'playwright-empty-password', display_name: 'Leerer Nutzer', invite_token: invitationData.token }),
  })
  if (!registration.ok) throw new Error(`Leeres Testkonto konnte nicht angelegt werden: ${registration.status} ${await registration.text()}`)
  const emptyTokens = await registration.json() as typeof tokens

  const storagePath = resolve(dirname(fileURLToPath(import.meta.url)), '.auth/user.json')
  await mkdir(dirname(storagePath), { recursive: true })
  await writeFile(storagePath, JSON.stringify({
    cookies: [],
    origins: [{ origin: webOrigin, localStorage: [{ name: 'avento.auth.tokens', value: JSON.stringify(tokens) }, { name: 'avento-color-mode', value: 'dark' }] }],
  }, null, 2))

  await writeFile(resolve(dirname(storagePath), 'empty-user.json'), JSON.stringify({
    cookies: [],
    origins: [{ origin: webOrigin, localStorage: [{ name: 'avento.auth.tokens', value: JSON.stringify(emptyTokens) }, { name: 'avento-color-mode', value: 'dark' }] }],
  }, null, 2))
  await writeFile(resolve(dirname(storagePath), 'fixtures.json'), JSON.stringify({ activities: importedActivities }, null, 2))
}
