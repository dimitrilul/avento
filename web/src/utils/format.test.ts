import { describe, expect, it } from 'vitest'
import { formatDistance, formatDuration, formatSpeedMps } from './format'

describe('deutsche Werteformatierung', () => {
  it('formatiert Meter als Kilometer', () => {
    expect(formatDistance(42_195)).toBe('42,2 km')
  })

  it('formatiert Sekunden als verständliche Fahrzeit', () => {
    expect(formatDuration(7_560)).toBe('2 Std. 06 Min.')
  })

  it('wandelt Meter pro Sekunde in Kilometer pro Stunde um', () => {
    expect(formatSpeedMps(10)).toBe('36 km/h')
  })
})
