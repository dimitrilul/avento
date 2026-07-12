import { describe, expect, it, vi } from 'vitest'
import { healthApi, healthEndpoints } from './health'

function jsonResponse(value: unknown) {
  return new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } })
}

describe('Google-Health-API-Vertrag', () => {
  it('verwendet ausschließlich die kanonischen Health-Routen und Payloads', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init?.method === 'DELETE') return new Response(null, { status: 204 })
      return jsonResponse({})
    })

    await healthApi.connection()
    await healthApi.startOAuth(true)
    await healthApi.sync(30)
    await healthApi.data({ dateFrom: '2026-06-13', dateTo: '2026-07-12', limit: 750 })
    await healthApi.overview('2026-07-12')
    await healthApi.disconnect()

    expect(fetchMock.mock.calls.map(([url, init]) => [url, init?.method ?? 'GET'])).toEqual([
      ['/api/v1/health/status', 'GET'],
      ['/api/v1/health/oauth/start?force_consent=true', 'POST'],
      ['/api/v1/health/sync', 'POST'],
      ['/api/v1/health/data?date_from=2026-06-13&date_to=2026-07-12&limit=750', 'GET'],
      ['/api/v1/health/overview?day=2026-07-12', 'GET'],
      ['/api/v1/health/connection', 'DELETE'],
    ])
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual({ lookback_days: 30 })
    expect(healthEndpoints.status).toBe('/health/status')
    expect(healthEndpoints.overview).toBe('/health/overview')
  })

  it('sendet bei Standardsynchronisation explizit null statt einen erfundenen Zeitraum', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({}))

    await healthApi.sync()

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ lookback_days: null })
  })
})

