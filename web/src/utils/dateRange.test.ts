import { describe, expect, it } from 'vitest'
import { currentWeekRange } from './dateRange'

describe('currentWeekRange', () => {
  it('liefert Montag bis heute statt der letzten sieben Tage', () => {
    expect(currentWeekRange(new Date('2026-07-15T18:30:00'))).toEqual({
      from: '2026-07-13',
      to: '2026-07-15',
    })
  })

  it('beginnt montags mit einem eintägigen Zeitraum', () => {
    expect(currentWeekRange(new Date('2026-07-13T08:00:00'))).toEqual({
      from: '2026-07-13',
      to: '2026-07-13',
    })
  })
})
