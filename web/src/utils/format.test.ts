import { describe, expect, it } from 'vitest'
import { formatClockDuration, formatDistance, formatDuration, formatHydration, formatSpeedMps } from './format'

describe('deutsche Werteformatierung', () => {
  it('formatiert Meter als Kilometer', () => {
    expect(formatDistance(42_195)).toBe('42,2 km')
  })

  it('formatiert Sekunden als verständliche Fahrzeit', () => {
    expect(formatDuration(7_560)).toBe('2 Std. 06 Min.')
  })

  it('formatiert Zeit für Diagramme als Stunden, Minuten und Sekunden', () => {
    expect(formatClockDuration(17_679)).toBe('04:54:39')
    expect(formatClockDuration(17_679, false)).toBe('04:54')
  })

  it('wandelt Meter pro Sekunde in Kilometer pro Stunde um', () => {
    expect(formatSpeedMps(10)).toBe('36 km/h')
  })

  it('formatiert Trinkmengen passend in Milliliter oder Liter', () => {
    expect(formatHydration(750)).toBe('750 ml')
    expect(formatHydration(1500)).toBe('1,5 l')
    expect(formatHydration(null)).toBe('–')
  })
})
