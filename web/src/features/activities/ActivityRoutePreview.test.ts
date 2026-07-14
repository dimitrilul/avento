import { describe, expect, it } from 'vitest'
import { routePreviewPath } from './ActivityRoutePreview'

describe('routePreviewPath', () => {
  it('erstellt aus GPS-Punkten einen begrenzten SVG-Pfad', () => {
    const path = routePreviewPath([
      { time: '2026-01-01T00:00:00Z', latitude: 52, longitude: 13 },
      { time: '2026-01-01T00:01:00Z', latitude: 52.01, longitude: 13.02 },
      { time: '2026-01-01T00:02:00Z', latitude: 52.02, longitude: 13.01 },
    ])
    expect(path).toMatch(/^M/)
    expect(path).toContain('L')
    for (const value of path!.match(/\d+(?:\.\d+)?/g)!.map(Number)) {
      expect(value).toBeGreaterThanOrEqual(0)
      expect(value).toBeLessThanOrEqual(240)
    }
  })

  it('liefert ohne ausreichende GPS-Daten einen ruhigen Fallback', () => {
    expect(routePreviewPath([{ time: '2026-01-01T00:00:00Z' }])).toBeNull()
  })
})
