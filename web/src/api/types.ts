export type ActivityType = 'ride' | 'training' | 'tour' | 'commute' | 'indoor' | 'other'

export interface HeartRateZone {
  name: string
  min_bpm: number
  max_bpm: number
  color: string
}

export interface Profile {
  id: string
  email: string
  display_name: string
  is_admin: boolean
  hr_max: number | null
  hr_rest: number | null
  hr_zones: HeartRateZone[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface AuthCredentials {
  email: string
  password: string
}

export interface RegistrationData extends AuthCredentials {
  display_name: string
  invite_token: string
}

export interface BootstrapData extends AuthCredentials {
  display_name: string
  bootstrap_code: string
}

export interface InvitationResponse {
  id: string
  token: string
  email: string | null
  expires_at: string
}

export interface PasswordResetResponse {
  token: string
  email: string
  expires_at: string
}

export interface TrackPoint {
  time: string
  latitude?: number | null
  longitude?: number | null
  altitude_m?: number | null
  distance_m?: number | null
  speed_mps?: number | null
  heart_rate_bpm?: number | null
  cadence_rpm?: number | null
  power_w?: number | null
}

export interface TrackResponse {
  activity_id: string
  points: TrackPoint[]
}

export interface WeatherData {
  provider?: string
  condition?: string | null
  weather_code?: number | null
  icon?: string | null
  temperature_c?: number | null
  apparent_temperature_c?: number | null
  feels_like_c?: number | null
  relative_humidity_percent?: number | null
  humidity_percent?: number | null
  wind_speed_kmh?: number | null
  wind_direction_deg?: number | null
  precipitation_mm?: number | null
  observed_at?: string | null
  is_estimated?: boolean
  [key: string]: unknown
}

export interface WeatherResponse {
  status: string
  data: WeatherData | null
  updated_at: string | null
}

export interface SummaryResponse {
  summary: string | null
  provider: string | null
  updated_at: string | null
}

export interface Activity {
  id: string
  title: string
  type: ActivityType | string
  notes: string | null
  started_at: string
  ended_at?: string | null
  created_at?: string
  updated_at?: string
  original_filename?: string
  distance_m: number
  duration_s: number
  moving_time_s: number
  pause_time_s?: number
  elevation_gain_m: number
  avg_speed_mps: number | null
  max_speed_mps: number | null
  avg_hr_bpm: number | null
  max_hr_bpm: number | null
  avg_power_w: number | null
  max_power_w?: number | null
  avg_cadence_rpm: number | null
  max_cadence_rpm?: number | null
  training_load?: number | null
  hr_zone_seconds?: Record<string, number>
  weather?: WeatherData | null
  weather_status?: string | null
  ai_summary?: string | null
  ai_provider?: string | null
}

export interface ActivityDetail extends Activity {
  track?: TrackResponse
}

export interface PaginatedActivities {
  items: Activity[]
  total: number
  limit: number
  offset: number
}

export interface ActivityFilters {
  q?: string
  type?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

export interface ActivityUpdate {
  title?: string
  type?: ActivityType | string
  notes?: string | null
}

export interface ImportActivityData extends ActivityUpdate {
  file: File
}

export interface StatisticsTotals {
  activities: number
  distance_m: number
  moving_time_s: number
  elevation_gain_m: number
  training_load?: number | null
}

export interface TrendPoint {
  month: string
  activity_count: number
  distance_m: number
  duration_s: number
  elevation_gain_m: number
  training_load?: number | null
}

export interface StatisticsOverview {
  activity_count: number
  distance_m: number
  duration_s: number
  moving_time_s: number
  elevation_gain_m: number
  training_load: number
  avg_speed_mps: number | null
  by_month: TrendPoint[]
}

export interface ActivityComparison {
  activities: Activity[]
}

export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>
  message?: string
}
