import { apiRequest } from './client'

export interface HealthOAuthStartResponse {
  authorization_url: string
  expires_at: string
  mock_mode: boolean
}

export interface HealthConnectionStatus {
  provider?: 'google_health_api_v4'
  enabled?: boolean
  mock_mode?: boolean
  connected: boolean
  status: string
  granted_scopes: string[]
  missing_scopes: string[]
  last_sync_at: string | null
  last_error_code: string | null
  data_sources?: Array<{
    platform: string | null
    recording_method?: string | null
    device_name: string | null
    device_manufacturer: string | null
    application_name: string | null
    last_seen_at: string | null
  }>
}

export interface HealthSyncResponse {
  run_id: string
  status: string
  range_start: string
  range_end: string
  fetched_count: number
  stored_count: number
  rejected_count: number
  error_code: string | null
}

export interface HealthMetric {
  metric_type: string
  value: number
  unit: string
  observed_at: string | null
  start_at: string | null
  end_at: string | null
  local_date: string | null
  imported_at: string
}

export interface HealthHeartRate {
  granularity: string
  start_at: string
  end_at: string
  local_date: string | null
  min_bpm: number
  avg_bpm: number
  max_bpm: number
  sleep_session_id: string | null
  exercise_id: string | null
}

export interface HealthSleepStage {
  start_at: string
  end_at: string
  stage_type: string
}

export interface HealthSleep {
  id: string
  start_at: string
  end_at: string
  local_date: string
  sleep_type: string
  is_nap: boolean
  minutes_asleep: number | null
  minutes_awake: number | null
  overlaps_other_session: boolean
  stages: HealthSleepStage[]
}

export interface HealthExercise {
  id: string
  start_at: string
  end_at: string
  local_date: string
  exercise_type: string
  title: string | null
  active_duration_seconds: number | null
  calories_kcal: number | null
  distance_m: number | null
  steps: number | null
  average_heart_rate_bpm: number | null
  active_zone_minutes: number | null
  heart_rate_zone_seconds: Record<string, number>
}

export interface HealthDataResponse {
  metrics: HealthMetric[]
  heart_rate: HealthHeartRate[]
  sleeps: HealthSleep[]
  exercises: HealthExercise[]
}

export interface HealthScoreFactor {
  key?: string
  label?: string
  current_value?: number | null
  unit?: string | null
  impact?: string
  contribution_points?: number
  reason?: string | null
  status?: string
}

export interface HealthScore {
  value?: number | null
  score?: number | null
  status?: string
  level?: string | null
  confidence?: string
  unit?: string
  raw_value?: number | null
  raw_unit?: string | null
  data_coverage?: {
    fraction?: number
    percent?: number
    missing_required_signals?: string[]
  }
  important_factors?: HealthScoreFactor[]
  factors?: HealthScoreFactor[]
  disclaimer?: string
}

export interface HealthOverviewResponse {
  date: string
  generated_at: string
  scores: Record<string, HealthScore | unknown>
  factors: HealthScoreFactor[]
  coverage: Record<string, number>
  baselines: Record<string, unknown>
  uncertainty: string[]
}

export interface HealthDataFilters {
  dateFrom?: string
  dateTo?: string
  limit?: number
}

export const healthEndpoints = {
  status: '/health/status',
  oauthStart: '/health/oauth/start',
  sync: '/health/sync',
  data: '/health/data',
  overview: '/health/overview',
  connection: '/health/connection',
} as const

export const healthQueryKeys = {
  all: ['health'] as const,
  connection: ['health', 'connection'] as const,
  overview: (day?: string) => ['health', 'overview', day ?? 'today'] as const,
  data: (filters: HealthDataFilters = {}) => [
    'health',
    'data',
    filters.dateFrom ?? '',
    filters.dateTo ?? '',
    filters.limit ?? 1000,
  ] as const,
}

function queryString(values: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

export const healthApi = {
  connection: () => apiRequest<HealthConnectionStatus>(healthEndpoints.status),
  startOAuth: (forceConsent = false) =>
    apiRequest<HealthOAuthStartResponse>(
      `${healthEndpoints.oauthStart}${queryString({ force_consent: forceConsent || undefined })}`,
      { method: 'POST' },
    ),
  sync: (lookbackDays?: number) =>
    apiRequest<HealthSyncResponse>(healthEndpoints.sync, {
      method: 'POST',
      body: { lookback_days: lookbackDays ?? null },
    }),
  data: (filters: HealthDataFilters = {}) =>
    apiRequest<HealthDataResponse>(
      `${healthEndpoints.data}${queryString({
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        limit: filters.limit,
      })}`,
    ),
  overview: (day?: string) =>
    apiRequest<HealthOverviewResponse>(
      `${healthEndpoints.overview}${queryString({ day })}`,
    ),
  disconnect: () => apiRequest<void>(healthEndpoints.connection, { method: 'DELETE' }),
}
