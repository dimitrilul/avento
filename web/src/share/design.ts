import type { OverlayTheme } from './types'

export const AVENTO_SOLID_COLORS = ['#0E6562', '#071C1B', '#F5F7F3', '#DDE9E1'] as const

export interface OverlayPalette {
  canvas: string
  surface: string
  surfaceStrong: string
  text: string
  muted: string
  accent: string
  achievement: string
  routeHalo: string
  shadow: string
}

export function paletteFor(theme: OverlayTheme): OverlayPalette {
  return theme === 'dark'
    ? {
        canvas: '#071C1B', surface: 'rgba(10, 40, 38, .88)', surfaceStrong: '#0D2A28',
        text: '#F7FBF9', muted: '#B7CAC5', accent: '#B8D95B', achievement: '#F2B85B',
        routeHalo: 'rgba(4, 20, 19, .82)', shadow: '0 18px 50px rgba(0, 0, 0, .28)',
      }
    : {
        canvas: '#F5F7F3', surface: 'rgba(255, 255, 255, .9)', surfaceStrong: '#FFFFFF',
        text: '#172322', muted: '#61706E', accent: '#0E6562', achievement: '#D77A30',
        routeHalo: 'rgba(255, 255, 255, .9)', shadow: '0 18px 50px rgba(20, 50, 45, .13)',
      }
}

export const overlayRadius = { small: 12, medium: 20, large: 32 }
