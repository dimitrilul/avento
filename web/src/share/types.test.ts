import { describe, expect, it } from 'vitest'
import { FORMAT_SPECS } from './types'
import { OVERLAY_TEMPLATES } from './templates'

describe('Overlay-Vertrag', () => {
  it('definiert die vier Social-Media-Formate in Exportauflösung', () => {
    expect(Object.fromEntries(Object.entries(FORMAT_SPECS).map(([key, value]) => [key, [value.exportWidth, value.exportHeight]]))).toEqual({
      square: [1080, 1080], portrait: [1080, 1350], story: [1080, 1920], landscape: [1920, 1080],
    })
  })

  it('registriert sechs eigenständige Vorlagen', () => {
    expect(OVERLAY_TEMPLATES.map((template) => template.id)).toEqual(['classic', 'minimal', 'photo', 'stats', 'map', 'achievement'])
    expect(new Set(OVERLAY_TEMPLATES.map((template) => template.render)).size).toBe(6)
  })
})
