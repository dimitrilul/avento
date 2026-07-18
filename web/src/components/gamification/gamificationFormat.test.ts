import { describe, expect, it } from 'vitest'
import { formatGamificationValue } from './gamificationFormat'

describe('formatGamificationValue', () => {
  it('zeigt kleinere Distanzen weiterhin in Metern', () => {
    expect(formatGamificationValue('distance_m', 850)).toBe('850 m')
  })

  it('formatiert größere Distanzen als gerundete Kilometer', () => {
    expect(formatGamificationValue('distance_m', 40_383.6)).toBe('40,4 km')
  })

  it('rundet Fahrzeit-Stunden auf ganze Stunden', () => {
    expect(formatGamificationValue('moving_time_s', 7_560)).toBe('2 Std.')
  })
})
