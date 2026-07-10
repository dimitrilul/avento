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
  training_goals: string[]
  avatar_data_url?: string | null
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
  data_basis: AIDataBasis | null
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
  ai_data_basis?: AIDataBasis | null
  hydration_ml?: number | null
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
  hydration_ml?: number | null
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
  avg_hr_bpm: number | null
  hydration_ml: number
  hydration_activity_count: number
  by_month: TrendPoint[]
  granularity: StatisticsGranularity
  series: StatisticsSeriesPoint[]
  comparison: StatisticsComparison | null
}

export type StatisticsGranularity = 'day' | 'week' | 'month' | 'auto'

export interface StatisticsSeriesPoint {
  period_start: string
  activity_count: number
  distance_m: number
  duration_s: number
  moving_time_s: number
  elevation_gain_m: number
  training_load: number
  avg_speed_mps: number | null
  avg_hr_bpm: number | null
  hydration_ml: number
  hydration_activity_count: number
}

export interface StatisticsComparison {
  date_from: string
  date_to: string
  activity_count: number
  distance_m: number
  duration_s: number
  moving_time_s: number
  elevation_gain_m: number
  training_load: number
  avg_speed_mps: number | null
  avg_hr_bpm: number | null
  hydration_ml: number
  hydration_activity_count: number
  changes: Record<string, number | null>
}

export interface ActivityComparisonMetric {
  activity_id: string
  title: string
  distance_m: number
  duration_s: number
  moving_time_s: number
  elevation_gain_m: number
  avg_speed_mps: number | null
  avg_hr_bpm: number | null
  max_hr_bpm: number | null
  efficiency_kmh_per_bpm: number | null
  headwind_kmh: number | null
  relative_score: number | null
}

export interface ActivityComparisonProfilePoint {
  progress_percent: number
  distance_km: number
  elevation_m: number | null
  speed_kmh: number | null
  heart_rate_bpm: number | null
}

export interface ActivityComparisonProfile {
  activity_id: string
  title: string
  points: ActivityComparisonProfilePoint[]
}

export interface ActivityComparison {
  activities: Activity[]
  metrics: ActivityComparisonMetric[]
  profiles: ActivityComparisonProfile[]
  ai_summary: string | null
  ai_provider: string | null
  ai_data_basis: AIDataBasis | null
}

export type ChatRole = 'user' | 'assistant'

export interface ChatHistoryItem {
  role: ChatRole
  content: string
}

export interface ChatSource {
  activity_id: string
  title: string
  started_at: string
}

export interface AIDataPeriod {
  started_at: string | null
  ended_at: string | null
  timezone: string | null
  label: string | null
}

export interface AIDataMetric {
  name: string
  value: unknown
  unit: string | null
  activity_id: string | null
  source: string
  method: string
}

export interface AIDataMethod {
  name: string
  description: string
  parameters: Record<string, unknown>
}

export interface AIDataBasis {
  schema_version: string
  generated_at: string
  period: AIDataPeriod | null
  activity_ids: string[]
  metrics: AIDataMetric[]
  methods: AIDataMethod[]
  limitations: string[]
  facts: Record<string, unknown>
}

export interface ChatResponse {
  answer: string
  provider: string
  sources: ChatSource[]
  tools_used: string[]
  data_basis: AIDataBasis | null
}

export interface ActivityPhoto {
  id: string
  activity_id: string
  caption: string | null
  captured_at: string | null
  latitude: number | null
  longitude: number | null
  original_filename: string
  content_type: string
  size_bytes: number
  width: number
  height: number
  file_url: string
  created_at: string
  updated_at: string
}

export interface ActivityPhotoListResponse {
  items: ActivityPhoto[]
  total: number
}

export interface ActivityPhotoUpload {
  file: File
  caption?: string | null
  captured_at?: string | null
  latitude?: number | null
  longitude?: number | null
}

export interface ActivityPhotoUpdate {
  caption?: string | null
  captured_at?: string | null
  latitude?: number | null
  longitude?: number | null
}

export interface DistanceRecord {
  target_distance_m: number
  duration_s: number
  avg_speed_mps: number
  activity_id: string
  title: string
  started_at: string
  source: string
  estimated: boolean
  segment_start_m: number
  segment_end_m: number
}

export interface ActivityRecord {
  activity_id: string
  title: string
  started_at: string
  distance_m: number
  moving_time_s: number
  avg_speed_mps: number
}

export interface PersonalRecordsResponse {
  generated_at: string
  distance_records: DistanceRecord[]
  longest_ride: ActivityRecord | null
  highest_average_speed: ActivityRecord | null
  methods: AIDataMethod[]
}

export interface InsightPeriod {
  date_from: string
  date_to: string
}

export interface InsightAggregate {
  period: string
  period_start: string
  period_end: string
  activity_count: number
  distance_m: number
  moving_time_s: number
  elevation_gain_m: number
  training_load: number
  avg_speed_mps: number | null
  avg_hr_bpm: number | null
  hydration_ml: number
  changes_from_previous: Record<string, number | null>
}

export interface FitnessTrend {
  status: string
  confidence: string
  sample_size: number
  speed_change_percent: number | null
  heart_rate_efficiency_change_percent: number | null
  statement: string
}

export interface InsightPattern {
  kind: string
  confidence: string
  sample_size: number
  statement: string
  evidence: Record<string, unknown>
  method: string
}

export interface LongTermInsightsResponse {
  generated_at: string
  period: InsightPeriod
  current: Record<string, unknown>
  previous_period: InsightPeriod
  previous: Record<string, unknown>
  changes: Record<string, number | null>
  monthly: InsightAggregate[]
  yearly: InsightAggregate[]
  fitness_trend: FitnessTrend
  patterns: InsightPattern[]
  methods: AIDataMethod[]
  disclaimer: string
}

export interface PeriodReviewResponse {
  year: number
  season: string
  period: InsightPeriod
  summary: string
  provider: string
  generated_at: string
  data_basis: AIDataBasis
}

export interface McpClient {
  client_id: string
  owner_user_id: string
  name: string
  scopes: string[]
  is_active: boolean
  revoked_at: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface McpClientCreate {
  owner_user_id: string
  name: string
  scopes: string[]
}

export interface McpClientCreated extends McpClient {
  client_secret: string
}

export interface McpClientUpdate {
  name?: string
  scopes?: string[]
  is_active?: boolean
}

export interface McpSecretRotated {
  client_id: string
  client_secret: string
}

export interface McpAccessTokenRequest {
  client_id: string
  client_secret: string
  scopes?: string[] | null
}

export interface McpAccessToken {
  access_token: string
  token_type: string
  expires_in: number
  scopes: string[]
}

export interface McpAuditEvent {
  client_id: string | null
  method: string
  tool_name: string | null
  outcome: string
  error_type: string | null
  jsonrpc_error_code: number | null
  http_status: number
  duration_ms: number
  created_at: string
}

export interface ApiErrorBody {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>
  message?: string
}
