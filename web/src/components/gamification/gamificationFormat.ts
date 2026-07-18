import type { GamificationMetric, GamificationPeriod } from '../../api'

const decimal = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 0 })
const distanceKilometres = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 })

export const gamificationMetricOptions: Array<{
  value: GamificationMetric
  label: string
  inputUnit: string
}> = [
  { value: 'distance_m', label: 'Distanz', inputUnit: 'km' },
  { value: 'activity_count', label: 'Anzahl Fahrten', inputUnit: 'Fahrten' },
  { value: 'elevation_gain_m', label: 'Höhenmeter', inputUnit: 'hm' },
  { value: 'moving_time_s', label: 'Fahrzeit', inputUnit: 'Std.' },
  { value: 'places_visited', label: 'Entdeckte Orte', inputUnit: 'Orte' },
]

export const gamificationPeriodOptions: Array<{ value: GamificationPeriod; label: string }> = [
  { value: 'week', label: 'Diese Woche' },
  { value: 'month', label: 'Dieser Monat' },
  { value: 'year', label: 'Dieses Jahr' },
  { value: 'custom', label: 'Eigener Zeitraum' },
]

export function metricLabel(metric: GamificationMetric) {
  return gamificationMetricOptions.find((option) => option.value === metric)?.label ?? 'Eigener Wert'
}

export function periodLabel(period: GamificationPeriod) {
  return gamificationPeriodOptions.find((option) => option.value === period)?.label ?? period
}

export function inputUnit(metric: GamificationMetric) {
  return gamificationMetricOptions.find((option) => option.value === metric)?.inputUnit ?? ''
}

export function toDisplayTarget(metric: GamificationMetric, value: number) {
  if (metric === 'distance_m') return value / 1000
  if (metric === 'moving_time_s') return value / 3600
  return value
}

export function toApiTarget(metric: GamificationMetric, value: number) {
  if (metric === 'distance_m') return value * 1000
  if (metric === 'moving_time_s') return value * 3600
  return value
}

export function formatGamificationValue(metric: GamificationMetric, value: number, unit?: string | null) {
  if (metric === 'distance_m') {
    return value >= 1000
      ? `${distanceKilometres.format(value / 1000)} km`
      : `${integer.format(value)} m`
  }
  if (metric === 'moving_time_s') return `${integer.format(value / 3600)} Std.`
  if (metric === 'activity_count') return `${integer.format(value)} ${value === 1 ? 'Fahrt' : 'Fahrten'}`
  if (metric === 'places_visited') return `${integer.format(value)} ${value === 1 ? 'Ort' : 'Orte'}`
  if (metric === 'elevation_gain_m') return `${integer.format(value)} hm`
  return [decimal.format(value), unit].filter(Boolean).join(' ')
}

export function formatXp(value: number) {
  return `${integer.format(value)} XP`
}
