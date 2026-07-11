import type { ActivityType } from '../api'

const number = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 0 })
const date = new Intl.DateTimeFormat('de-DE', {
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})
const dateTime = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export const formatDistance = (metres?: number | null) =>
  metres == null ? '–' : `${number.format(metres / 1000)} km`

export const formatElevation = (metres?: number | null) =>
  metres == null ? '–' : `${integer.format(metres)} m`

export const formatSpeed = (speed?: number | null) =>
  speed == null ? '–' : `${number.format(speed)} km/h`

export const formatSpeedMps = (speed?: number | null) => formatSpeed(speed == null ? speed : speed * 3.6)

export const formatHeartRate = (bpm?: number | null) =>
  bpm == null ? '–' : `${integer.format(bpm)} bpm`

export const formatPower = (watts?: number | null) =>
  watts == null ? '–' : `${integer.format(watts)} W`

export const formatHydration = (millilitres?: number | null) => {
  if (millilitres == null) return '–'
  if (millilitres >= 1000) {
    return `${new Intl.NumberFormat('de-DE', { maximumFractionDigits: 2 }).format(millilitres / 1000)} l`
  }
  return `${integer.format(millilitres)} ml`
}

export const formatDuration = (seconds?: number | null) => {
  if (seconds == null) return '–'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return hours ? `${hours} Std. ${minutes.toString().padStart(2, '0')} Min.` : `${minutes} Min.`
}

/** Formats a duration for charts and compact time displays as HH:MM(:SS). */
export const formatClockDuration = (seconds?: number | null, includeSeconds = true) => {
  if (seconds == null || !Number.isFinite(seconds)) return '–'
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remainder = total % 60
  const base = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  return includeSeconds ? `${base}:${String(remainder).padStart(2, '0')}` : base
}

export const formatDate = (value?: string | null) => (value ? date.format(new Date(value)) : '–')
export const formatDateTime = (value?: string | null) =>
  value ? dateTime.format(new Date(value)) : '–'

export const formatChartValue = (value: unknown, maximumFractionDigits = 1) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '–'
  return value.toLocaleString('de-DE', { maximumFractionDigits })
}

export const activityTypeLabels: Record<string, string> = {
  ride: 'Radfahrt',
  training: 'Training',
  tour: 'Tour',
  commute: 'Pendeln',
  indoor: 'Indoor',
  other: 'Sonstiges',
}

export const activityTypes: Array<{ value: ActivityType; label: string }> = [
  { value: 'ride', label: 'Radfahrt' },
  { value: 'training', label: 'Training' },
  { value: 'tour', label: 'Tour' },
  { value: 'commute', label: 'Pendeln' },
  { value: 'indoor', label: 'Indoor' },
  { value: 'other', label: 'Sonstiges' },
]

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Etwas ist schiefgelaufen.'
}
