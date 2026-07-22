import { afterEach, describe, expect, it, vi } from 'vitest'
import { tokenStore } from './client'
import { activityPhotosApi, insightsApi, mcpAdminApi } from './roadmap'
import type { ActivityPhoto } from './types'

const photo: ActivityPhoto = {
  id: 'photo-1',
  activity_id: 'ride-1',
  original_filename: 'passhöhe.jpg',
  content_type: 'image/webp',
  size_bytes: 1234,
  original_size_bytes: 2345,
  width: 1200,
  height: 800,
  captured_at: '2026-07-10T08:30:00Z',
  latitude: 47.1,
  longitude: 11.2,
  caption: 'Passhöhe',
  file_url: '/api/v1/activities/ride-1/photos/photo-1/file',
  original_file_url: '/api/v1/activities/ride-1/photos/photo-1/original',
  processing_status: 'ready',
  created_at: '2026-07-10T09:00:00Z',
  updated_at: '2026-07-10T09:00:00Z',
}

function jsonResponse(value: unknown) {
  return new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => tokenStore.clear())

describe('Roadmap-API-Verträge', () => {
  it('sendet Foto und Metadaten an den Aktivitätsfoto-Endpunkt', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => jsonResponse(photo))
    const file = new File(['bild'], 'passhöhe.jpg', { type: 'image/jpeg' })

    await activityPhotosApi.upload('ride-1', {
      file,
      caption: ' Passhöhe ',
      captured_at: '2026-07-10T08:30:00.000Z',
      latitude: 47.1,
      longitude: 11.2,
    })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/activities/ride-1/photos')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBeInstanceOf(FormData)
    const body = init?.body as FormData
    expect(body.get('file')).toBe(file)
    expect(body.get('caption')).toBe('Passhöhe')
    expect(body.get('captured_at')).toBe('2026-07-10T08:30:00.000Z')
    expect(body.get('latitude')).toBe('47.1')
    expect(body.get('client_timezone')).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone)
  })

  it('kann mehrere Fotos als getrennte Uploads mit eigenem Fortschritt senden', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => jsonResponse(photo))
    const files = [
      new File(['erstes bild'], 'erstes.jpg', { type: 'image/jpeg' }),
      new File(['zweites bild'], 'zweites.png', { type: 'image/png' }),
    ]

    await Promise.all(files.map((file) => activityPhotosApi.upload('ride-1', { file })))

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls.map(([, init]) => (init?.body as FormData).get('file'))).toEqual(files)
  })

  it('lädt file_url mit dem angemeldeten Zugriffstoken', async () => {
    tokenStore.set({ access_token: 'user-token', refresh_token: 'refresh-token', token_type: 'bearer', expires_in: 900 })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(new Blob(['foto']), { status: 200, headers: { 'Content-Type': 'image/webp' } }))

    const result = await activityPhotosApi.file(photo)

    expect(result.type).toBe('image/webp')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(photo.file_url)
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer user-token')
  })

  it('verwendet die finalen Records-, Insights- und Review-Pfade', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => jsonResponse({}))

    await insightsApi.records()
    await insightsApi.longTerm('2024-01-01', '2026-07-10')
    await insightsApi.periodReview(2026, 'summer')

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/statistics/records',
      '/api/v1/statistics/insights?date_from=2024-01-01&date_to=2026-07-10',
      '/api/v1/statistics/reviews/2026?season=summer',
    ])
  })

  it('sendet beim MCP-Token-Endpunkt kein Benutzer-Bearer-Token', async () => {
    tokenStore.set({ access_token: 'user-token', refresh_token: 'refresh-token', token_type: 'bearer', expires_in: 900 })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ access_token: 'mcp-token', token_type: 'bearer', expires_in: 900, scopes: ['activities:read'] }))

    await mcpAdminApi.requestToken({ client_id: 'avento-client-1', client_secret: 'x'.repeat(32), scopes: ['activities:read'] })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/mcp/token')
    expect(new Headers(init?.headers).has('Authorization')).toBe(false)
  })
})
