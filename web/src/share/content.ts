import type { Activity, StatisticsOverview } from '../api'
import {
  formatDistance,
  formatDuration,
  formatElevation,
  formatHeartRate,
  formatHydration,
  formatSpeedMps,
} from '../utils/format'
import type { MetricKey, ShareContent } from './types'

export interface OverlayMetricValue {
  key: MetricKey
  label: string
  value: string
  available: boolean
}

function duration(value: number) {
  return formatDuration(value).replace(' Std. ', ':').replace(' Min.', '').replace(' Sek.', ' s')
}

function activityMetrics(activity: Activity): Record<MetricKey, OverlayMetricValue> {
  const metric = (key: MetricKey, label: string, value: string, available = true): OverlayMetricValue => ({ key, label, value, available })
  return {
    distance: metric('distance', 'Distanz', formatDistance(activity.distance_m)),
    movingTime: metric('movingTime', 'Fahrzeit', duration(activity.moving_time_s)),
    duration: metric('duration', 'Gesamtzeit', duration(activity.duration_s)),
    elevation: metric('elevation', 'Höhenmeter', formatElevation(activity.elevation_gain_m)),
    avgSpeed: metric('avgSpeed', 'Ø Tempo', formatSpeedMps(activity.avg_speed_mps), activity.avg_speed_mps != null),
    maxSpeed: metric('maxSpeed', 'Max. Tempo', formatSpeedMps(activity.max_speed_mps), activity.max_speed_mps != null),
    heartRate: metric('heartRate', 'Ø Puls', formatHeartRate(activity.avg_hr_bpm), activity.avg_hr_bpm != null),
    power: metric('power', 'Ø Leistung', activity.avg_power_w == null ? '–' : `${Math.round(activity.avg_power_w)} W`, activity.avg_power_w != null),
    cadence: metric('cadence', 'Ø Trittfrequenz', activity.avg_cadence_rpm == null ? '–' : `${Math.round(activity.avg_cadence_rpm)} rpm`, activity.avg_cadence_rpm != null),
    hydration: metric('hydration', 'Trinkmenge', formatHydration(activity.hydration_ml), activity.hydration_ml != null),
    activities: metric('activities', 'Aktivitäten', '1'),
    trainingLoad: metric('trainingLoad', 'Trainingslast', activity.training_load == null ? '–' : `${Math.round(activity.training_load)}`, activity.training_load != null),
  }
}

function periodMetrics(stats: StatisticsOverview): Record<MetricKey, OverlayMetricValue> {
  const metric = (key: MetricKey, label: string, value: string, available = true): OverlayMetricValue => ({ key, label, value, available })
  return {
    activities: metric('activities', 'Aktivitäten', String(stats.activity_count)),
    distance: metric('distance', 'Distanz', formatDistance(stats.distance_m)),
    movingTime: metric('movingTime', 'Fahrzeit', duration(stats.moving_time_s)),
    duration: metric('duration', 'Gesamtzeit', duration(stats.duration_s)),
    elevation: metric('elevation', 'Höhenmeter', formatElevation(stats.elevation_gain_m)),
    avgSpeed: metric('avgSpeed', 'Ø Tempo', formatSpeedMps(stats.avg_speed_mps), stats.avg_speed_mps != null),
    heartRate: metric('heartRate', 'Ø Puls', formatHeartRate(stats.avg_hr_bpm), stats.avg_hr_bpm != null),
    trainingLoad: metric('trainingLoad', 'Trainingslast', `${Math.round(stats.training_load)}`),
    hydration: metric('hydration', 'Trinkmenge', formatHydration(stats.hydration_ml), stats.hydration_activity_count > 0),
    maxSpeed: metric('maxSpeed', 'Max. Tempo', '–', false),
    power: metric('power', 'Ø Leistung', '–', false),
    cadence: metric('cadence', 'Ø Trittfrequenz', '–', false),
  }
}

export function metricValues(content: ShareContent, selected: MetricKey[]) {
  const values = content.kind === 'activity' ? activityMetrics(content.activity) : periodMetrics(content.statistics)
  return selected.map((key) => values[key]).filter((item) => item.available)
}

export function availableMetrics(content: ShareContent) {
  const values = content.kind === 'activity' ? activityMetrics(content.activity) : periodMetrics(content.statistics)
  return Object.values(values).filter((item) => item.available)
}

export function contentTitle(content: ShareContent) {
  return content.kind === 'activity' ? content.activity.title : content.title
}

export function contentDate(content: ShareContent) {
  if (content.kind === 'period') return content.dateLabel
  return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'long', year: 'numeric' }).format(new Date(content.activity.started_at))
}

export function weatherLabel(content: ShareContent) {
  if (content.kind !== 'activity') return null
  const weather = content.activity.weather
  if (!weather) return null
  const condition = typeof weather.condition === 'string' ? weather.condition : null
  const temperature = typeof weather.temperature_c === 'number' ? `${Math.round(weather.temperature_c)}°` : null
  return [condition, temperature].filter(Boolean).join(' · ') || null
}
