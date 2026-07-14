import { apiRequest } from './client'
import type {
  GamificationAnnualAward,
  GamificationBadge,
  GamificationChallenge,
  GamificationDiscovery,
  GamificationDiscoveryBackfillResult,
  GamificationDiscoveryScope,
  GamificationGoal,
  GamificationGoalInput,
  GamificationGoalUpdate,
  GamificationLevel,
  GamificationMetric,
  GamificationOverview,
  GamificationRecordChase,
  GamificationStreak,
} from './types'

type JsonObject = Record<string, unknown>

/**
 * Alle vertragsspezifischen Pfade stehen bewusst an einer Stelle. Falls der
 * Backend-Vertrag vor dem Merge noch leicht umbenannt wird, bleibt die
 * Anpassung damit auf dieses Modul begrenzt.
 */
export const gamificationEndpoints = {
  overview: '/gamification/overview',
  goals: '/gamification/goals',
  goal: (goalId: string) => `/gamification/goals/${encodeURIComponent(goalId)}`,
  acceptChallenge: (challengeId: string) => `/gamification/challenges/${encodeURIComponent(challengeId)}/accept`,
  declineChallenge: (challengeId: string) => `/gamification/challenges/${encodeURIComponent(challengeId)}/decline`,
  discoveryBackfill: '/gamification/discoveries/backfill',
} as const

export const gamificationOverviewQueryKey = ['gamification', 'overview'] as const

const emptyLevel: GamificationLevel = {
  level: 1,
  name: 'Entdecker:in',
  total_xp: 0,
  current_xp: 0,
  next_level_xp: 100,
  progress_percent: 0,
  breakdown: {},
}

function asObject(value: unknown): JsonObject {
  return value != null && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : {}
}

function first(object: JsonObject, keys: string[]) {
  for (const key of keys) {
    if (object[key] !== undefined && object[key] !== null) return object[key]
  }
  return undefined
}

function asString(value: unknown, fallback = '') {
  return typeof value === 'string' ? value : typeof value === 'number' ? String(value) : fallback
}

function asNullableString(value: unknown) {
  const text = asString(value).trim()
  return text || null
}

function asNumber(value: unknown, fallback = 0) {
  const number = typeof value === 'number' ? value : typeof value === 'string' && value.trim() ? Number(value) : Number.NaN
  return Number.isFinite(number) ? number : fallback
}

function asNullableNumber(value: unknown) {
  if (value === null || value === undefined || value === '') return null
  const number = asNumber(value, Number.NaN)
  return Number.isFinite(number) ? number : null
}

function asBoolean(value: unknown, fallback = false) {
  if (typeof value === 'boolean') return value
  if (value === 1 || value === '1' || value === 'true') return true
  if (value === 0 || value === '0' || value === 'false') return false
  return fallback
}

function asArray(value: unknown): unknown[] {
  if (Array.isArray(value)) return value
  const object = asObject(value)
  return Array.isArray(object.items) ? object.items : []
}

function asStringArray(value: unknown) {
  return asArray(value).map((item) => {
    if (typeof item === 'string') return item
    return asString(first(asObject(item), ['name', 'label', 'title']))
  }).filter(Boolean)
}

function asNumberRecord(value: unknown) {
  return Object.fromEntries(
    Object.entries(asObject(value))
      .map(([key, item]) => [key, asNumber(item, Number.NaN)] as const)
      .filter(([, item]) => Number.isFinite(item)),
  )
}

function percent(value: unknown, current: number, target: number) {
  const calculated = target > 0 ? current / target * 100 : 0
  return Math.max(0, Math.min(100, asNumber(value, calculated)))
}

function defaultUnit(metric: GamificationMetric) {
  if (metric === 'distance_m') return 'km'
  if (metric === 'elevation_gain_m') return 'hm'
  if (metric === 'moving_time_s') return 'Std.'
  if (metric === 'activity_count') return 'Fahrten'
  if (metric === 'places_visited') return 'Orte'
  return ''
}

function normalizeLevel(value: unknown): GamificationLevel {
  const object = asObject(value)
  const currentXp = Math.max(0, asNumber(first(object, ['current_xp', 'level_xp', 'xp_in_level', 'xp'])))
  const nextLevelXp = Math.max(1, asNumber(first(object, ['next_level_xp', 'xp_for_next_level', 'level_target_xp', 'xp_target']), 100))
  return {
    level: Math.max(1, Math.round(asNumber(first(object, ['level', 'current_level', 'number']), 1))),
    name: asString(first(object, ['name', 'title', 'label']), emptyLevel.name),
    total_xp: Math.max(0, asNumber(first(object, ['total_xp', 'xp_total']), currentXp)),
    current_xp: currentXp,
    next_level_xp: nextLevelXp,
    progress_percent: percent(first(object, ['progress_percent', 'progress']), currentXp, nextLevelXp),
    breakdown: asNumberRecord(first(object, ['breakdown', 'xp_breakdown'])),
  }
}

export function normalizeGamificationGoal(value: unknown): GamificationGoal {
  const object = asObject(value)
  const metric = asString(first(object, ['metric', 'metric_type', 'kind']), 'custom') as GamificationMetric
  const currentValue = Math.max(0, asNumber(first(object, ['current_value', 'current', 'value', 'progress_value'])))
  const targetValue = Math.max(0, asNumber(first(object, ['target_value', 'target', 'goal_value'])))
  const progress = percent(first(object, ['progress_percent', 'progress']), currentValue, targetValue)
  const completedAt = asNullableString(first(object, ['completed_at', 'achieved_at']))
  return {
    id: asString(first(object, ['id', 'goal_id'])),
    title: asString(first(object, ['title', 'name', 'label']), 'Persönliches Ziel'),
    description: asNullableString(first(object, ['description', 'summary'])),
    metric,
    current_value: currentValue,
    target_value: targetValue,
    unit: asString(first(object, ['unit', 'display_unit']), defaultUnit(metric)),
    period: asString(first(object, ['period', 'timeframe', 'interval']), 'custom'),
    progress_percent: progress,
    remaining_value: Math.max(0, asNumber(first(object, ['remaining_value', 'remaining']), targetValue - currentValue)),
    status: asString(first(object, ['status']), completedAt || progress >= 100 ? 'completed' : 'active'),
    starts_at: asNullableString(first(object, ['starts_at', 'start_date', 'started_at'])),
    deadline: asNullableString(first(object, ['deadline', 'ends_at', 'end_date'])),
    completed_at: completedAt,
    reward_xp: Math.max(0, Math.round(asNumber(first(object, ['reward_xp', 'xp_reward'])))),
    created_at: asNullableString(first(object, ['created_at'])),
    updated_at: asNullableString(first(object, ['updated_at'])),
  }
}

function normalizeChallenge(value: unknown, fallbackStatus = 'suggested'): GamificationChallenge {
  const object = asObject(value)
  const metric = asString(first(object, ['metric', 'metric_type', 'kind']), 'custom') as GamificationMetric
  const currentValue = Math.max(0, asNumber(first(object, ['current_value', 'current', 'value', 'progress_value'])))
  const targetValue = Math.max(0, asNumber(first(object, ['target_value', 'target', 'goal_value'])))
  const source = asString(first(object, ['source', 'origin'])).toLowerCase()
  return {
    id: asString(first(object, ['id', 'challenge_id'])),
    title: asString(first(object, ['title', 'name', 'label']), 'Persönliche Challenge'),
    description: asString(first(object, ['description', 'summary', 'reason'])),
    metric,
    current_value: currentValue,
    target_value: targetValue,
    unit: asString(first(object, ['unit', 'display_unit']), defaultUnit(metric)),
    progress_percent: percent(first(object, ['progress_percent', 'progress']), currentValue, targetValue),
    remaining_value: Math.max(0, asNumber(first(object, ['remaining_value', 'remaining']), targetValue - currentValue)),
    duration_days: Math.max(1, Math.round(asNumber(first(object, ['duration_days', 'days']), 7))),
    reward_xp: Math.max(0, Math.round(asNumber(first(object, ['reward_xp', 'xp_reward', 'xp'])))),
    status: asString(first(object, ['status']), fallbackStatus),
    source: source || 'local',
    ai_generated: asBoolean(first(object, ['ai_generated', 'is_ai_generated']), source === 'ai' || source === 'assistant'),
    personalization_reason: asNullableString(first(object, ['personalization_reason', 'reason'])),
    weather_sensitive: asBoolean(first(object, ['weather_sensitive', 'weather_dependent', 'requires_safe_weather'])),
    safety_note: asNullableString(first(object, ['safety_note', 'weather_safety_note', 'safety_hint'])),
    starts_at: asNullableString(first(object, ['starts_at', 'start_date'])),
    expires_at: asNullableString(first(object, ['expires_at', 'valid_until'])),
    accepted_at: asNullableString(first(object, ['accepted_at'])),
    completed_at: asNullableString(first(object, ['completed_at', 'achieved_at'])),
    created_at: asNullableString(first(object, ['created_at'])),
    updated_at: asNullableString(first(object, ['updated_at'])),
  }
}

function normalizeBadge(value: unknown): GamificationBadge {
  const object = asObject(value)
  const currentValue = Math.max(0, asNumber(first(object, ['current_value', 'current', 'progress_value'])))
  const targetValue = Math.max(0, asNumber(first(object, ['target_value', 'target'])))
  const unlockedAt = asNullableString(first(object, ['unlocked_at', 'earned_at', 'achieved_at']))
  const unlocked = asBoolean(first(object, ['unlocked', 'earned', 'is_unlocked']), Boolean(unlockedAt))
  return {
    id: asString(first(object, ['id', 'badge_id', 'key'])),
    key: asString(first(object, ['key', 'badge_key', 'id'])),
    name: asString(first(object, ['name', 'title', 'label']), 'Abzeichen'),
    description: asString(first(object, ['description', 'summary'])),
    category: asString(first(object, ['category', 'group']), 'Allgemein'),
    tier: asString(first(object, ['tier']), 'standard'),
    icon: asNullableString(first(object, ['icon', 'icon_name'])),
    reward_xp: Math.max(0, Math.round(asNumber(first(object, ['reward_xp', 'xp_reward'])))),
    unlocked,
    unlocked_at: unlockedAt,
    source_activity_id: asNullableString(first(object, ['source_activity_id', 'activity_id'])),
    current_value: currentValue,
    target_value: targetValue,
    unit: asString(first(object, ['unit', 'display_unit'])),
    progress_percent: unlocked ? 100 : percent(first(object, ['progress_percent', 'progress']), currentValue, targetValue),
  }
}

function normalizeStreak(value: unknown): GamificationStreak {
  const object = asObject(value)
  return {
    current_weeks: Math.max(0, Math.round(asNumber(first(object, ['current_weeks', 'current', 'weeks'])))),
    best_weeks: Math.max(0, Math.round(asNumber(first(object, ['best_weeks', 'longest_weeks', 'best'])))),
    weekly_target: Math.max(1, Math.round(asNumber(first(object, ['weekly_target', 'target_per_week', 'target']), 1))),
    current_week_progress: Math.max(0, Math.round(asNumber(first(object, ['current_week_progress', 'activities_this_week', 'week_progress'])))),
    pause_protection_available: asBoolean(first(object, ['pause_protection_available', 'freeze_available', 'streak_freeze_available'])),
    pause_protection_active: asBoolean(first(object, ['pause_protection_active', 'freeze_active', 'is_protected'])),
    protected_until: asNullableString(first(object, ['protected_until', 'freeze_until'])),
    next_check_at: asNullableString(first(object, ['next_check_at', 'week_ends_at', 'deadline'])),
    active_week_starts: asStringArray(first(object, ['active_week_starts', 'active_weeks'])),
    method: asString(first(object, ['method'])),
  }
}

function normalizeRecordChase(value: unknown): GamificationRecordChase {
  const object = asObject(value)
  const metric = asString(first(object, ['metric', 'metric_type', 'kind']), 'custom') as GamificationMetric
  const currentValue = Math.max(0, asNumber(first(object, ['current_value', 'current', 'record_value', 'value'])))
  const targetValue = Math.max(0, asNumber(first(object, ['target_value', 'target', 'next_target'])))
  return {
    id: asString(first(object, ['id', 'record_id', 'key'])),
    title: asString(first(object, ['title', 'name', 'label']), 'Persönlicher Rekord'),
    description: asString(first(object, ['description', 'summary'])),
    metric,
    current_value: currentValue,
    target_value: targetValue,
    unit: asString(first(object, ['unit', 'display_unit']), defaultUnit(metric)),
    progress_percent: percent(first(object, ['progress_percent', 'progress']), currentValue, targetValue),
    activity_id: asNullableString(first(object, ['activity_id', 'record_activity_id'])),
    achieved: asBoolean(first(object, ['achieved', 'completed']), targetValue > 0 && currentValue >= targetValue),
  }
}

const discoveryLabels: Record<string, string> = {
  village: 'Dörfer',
  villages: 'Dörfer',
  municipality: 'Städte & Kommunen',
  municipalities: 'Städte & Kommunen',
  city: 'Städte & Kommunen',
  cities: 'Städte & Kommunen',
  city_municipality: 'Städte & Kommunen',
  state: 'Bundesländer',
  states: 'Bundesländer',
  country: 'Länder',
  countries: 'Länder',
}

function normalizeDiscoveryScope(scope: string): GamificationDiscoveryScope {
  if (scope === 'villages') return 'village'
  if (scope === 'municipalities' || scope === 'city' || scope === 'cities' || scope === 'city_municipality') return 'municipality'
  if (scope === 'states') return 'state'
  if (scope === 'countries') return 'country'
  return scope as GamificationDiscoveryScope
}

function normalizeDiscovery(value: unknown, fallbackScope = ''): GamificationDiscovery {
  const object = asObject(value)
  const rawScope = asString(first(object, ['scope', 'type', 'level']), fallbackScope).toLowerCase()
  const scope = normalizeDiscoveryScope(rawScope)
  const places = asStringArray(first(object, ['places', 'items', 'names', 'recent']))
  const totalAvailable = asNullableNumber(first(object, ['total_available', 'total', 'possible']))
  const count = Math.max(0, Math.round(asNumber(first(object, ['count', 'visited_count']), places.length)))
  return {
    scope,
    label: asString(first(object, ['label', 'title']), discoveryLabels[rawScope] ?? rawScope),
    count,
    total_available: totalAvailable,
    progress_percent: totalAvailable && totalAvailable > 0
      ? percent(first(object, ['progress_percent', 'progress']), count, totalAvailable)
      : asNullableNumber(first(object, ['progress_percent', 'progress'])),
    places,
  }
}

function normalizeDiscoveries(value: unknown) {
  const normalized = Array.isArray(value)
    ? value.map((item) => normalizeDiscovery(item))
    : Object.entries(asObject(value))
      .filter(([key]) => key in discoveryLabels)
      .map(([scope, entry]) => normalizeDiscovery(entry, scope))

  return normalized.reduce<GamificationDiscovery[]>((items, discovery) => {
    const existing = items.find((item) => item.scope === discovery.scope)
    if (!existing) return [...items, discovery]
    const count = existing.count + discovery.count
    const totalAvailable = existing.total_available != null && discovery.total_available != null
      ? existing.total_available + discovery.total_available
      : existing.total_available ?? discovery.total_available
    existing.count = count
    existing.total_available = totalAvailable
    existing.progress_percent = totalAvailable && totalAvailable > 0 ? Math.min(100, count / totalAvailable * 100) : null
    existing.places = [...new Set([...existing.places, ...discovery.places])]
    return items
  }, [])
}

function normalizeAnnualAward(value: unknown): GamificationAnnualAward {
  const object = asObject(value)
  const earnedAt = asNullableString(first(object, ['earned_at', 'unlocked_at', 'awarded_at']))
  return {
    id: asString(first(object, ['id', 'award_id', 'key'])),
    key: asString(first(object, ['key', 'award_key', 'id'])),
    year: Math.round(asNumber(first(object, ['year']), new Date().getFullYear())),
    title: asString(first(object, ['title', 'name', 'label']), 'Jahresauszeichnung'),
    description: asString(first(object, ['description', 'summary'])),
    value: asNullableNumber(first(object, ['value', 'result'])),
    unit: asNullableString(first(object, ['unit', 'display_unit'])),
    tier: asString(first(object, ['tier']), 'standard'),
    earned: asBoolean(first(object, ['earned', 'unlocked', 'awarded']), Boolean(earnedAt)),
    earned_at: earnedAt,
    icon: asNullableString(first(object, ['icon', 'icon_name'])),
    reward_xp: Math.max(0, Math.round(asNumber(first(object, ['reward_xp', 'xp_reward'])))),
    is_final: asBoolean(first(object, ['is_final', 'final'])),
  }
}

function normalizeGeocoding(value: unknown): GamificationOverview['geocoding'] {
  const object = asObject(value)
  const rawStatus = asString(first(object, ['status']), 'disabled')
  const status = ['disabled', 'misconfigured', 'ready', 'rate_limited'].includes(rawStatus)
    ? rawStatus as GamificationOverview['geocoding']['status']
    : 'misconfigured'
  return {
    status,
    provider: asNullableString(first(object, ['provider'])),
    attribution_label: asNullableString(first(object, ['attribution_label', 'attribution'])),
    attribution_url: asNullableString(first(object, ['attribution_url'])),
  }
}

function normalizeBackfill(value: unknown): GamificationDiscoveryBackfillResult {
  const object = asObject(value)
  return {
    processed: Math.max(0, Math.round(asNumber(object.processed))),
    available: Math.max(0, Math.round(asNumber(object.available))),
    failed: Math.max(0, Math.round(asNumber(object.failed))),
    remaining: Math.max(0, Math.round(asNumber(object.remaining))),
    total: Math.max(0, Math.round(asNumber(object.total))),
    rate_limited: asBoolean(object.rate_limited),
    retry_after_seconds: asNullableNumber(object.retry_after_seconds),
  }
}

/** Mappt kleine Feldnamensabweichungen auf das stabile UI-Modell. */
export function normalizeGamificationOverview(value: unknown): GamificationOverview {
  const response = asObject(value)
  const object = Object.keys(asObject(response.data)).length ? asObject(response.data) : response
  const combinedChallenges = asArray(first(object, ['challenges'])).map((item) => normalizeChallenge(item))
  const suggestions = asArray(first(object, ['challenge_suggestions', 'suggestions', 'ai_challenges']))
    .map((item) => normalizeChallenge(item, 'suggested'))
  const explicitActive = asArray(first(object, ['active_challenges', 'accepted_challenges']))
    .map((item) => normalizeChallenge(item, 'accepted'))
  const challengeSuggestions = suggestions.length
    ? suggestions
    : combinedChallenges.filter((challenge) => challenge.status === 'suggested')
  const activeChallenges = explicitActive.length
    ? explicitActive
    : combinedChallenges.filter((challenge) => ['accepted', 'active', 'completed'].includes(challenge.status))

  return {
    generated_at: asNullableString(first(object, ['generated_at', 'updated_at'])),
    privacy: asString(first(object, ['privacy']), 'private'),
    level: normalizeLevel(first(object, ['level', 'xp', 'progression'])),
    goals: asArray(first(object, ['goals', 'personal_goals'])).map(normalizeGamificationGoal),
    active_challenges: activeChallenges,
    challenge_suggestions: challengeSuggestions,
    ai_challenges_available: asBoolean(
      first(object, ['ai_challenges_available', 'suggestions_available', 'ai_available']),
      challengeSuggestions.length > 0,
    ),
    badges: asArray(first(object, ['badges', 'achievements'])).map(normalizeBadge),
    streak: normalizeStreak(first(object, ['streak', 'weekly_streak'])),
    record_chases: asArray(first(object, ['record_chases', 'records', 'personal_records'])).map(normalizeRecordChase),
    discoveries: normalizeDiscoveries(first(object, ['discoveries', 'exploration'])),
    geocoding: normalizeGeocoding(first(object, ['geocoding', 'geocoder'])),
    annual_awards: asArray(first(object, ['annual_awards', 'yearly_awards', 'awards'])).map(normalizeAnnualAward),
  }
}

function goalPayload(input: GamificationGoalInput | GamificationGoalUpdate) {
  const payload: GamificationGoalUpdate = { ...input }
  if (input.title !== undefined) payload.title = input.title.trim()
  if ('deadline' in input) payload.deadline = input.deadline || null
  return payload
}

export const gamificationApi = {
  async overview() {
    return normalizeGamificationOverview(await apiRequest<unknown>(gamificationEndpoints.overview))
  },
  async createGoal(input: GamificationGoalInput) {
    return normalizeGamificationGoal(await apiRequest<unknown>(gamificationEndpoints.goals, {
      method: 'POST',
      body: goalPayload(input),
    }))
  },
  async updateGoal(goalId: string, input: GamificationGoalUpdate) {
    return normalizeGamificationGoal(await apiRequest<unknown>(gamificationEndpoints.goal(goalId), {
      method: 'PATCH',
      body: goalPayload(input),
    }))
  },
  deleteGoal: (goalId: string) => apiRequest<void>(gamificationEndpoints.goal(goalId), { method: 'DELETE' }),
  async acceptChallenge(challengeId: string) {
    const response = await apiRequest<unknown>(gamificationEndpoints.acceptChallenge(challengeId), { method: 'POST' })
    return response == null ? null : normalizeChallenge(response, 'accepted')
  },
  async declineChallenge(challengeId: string) {
    const response = await apiRequest<unknown>(gamificationEndpoints.declineChallenge(challengeId), { method: 'POST' })
    return response == null ? null : normalizeChallenge(response, 'declined')
  },
  async backfillDiscoveries(retryFailed = false) {
    return normalizeBackfill(await apiRequest<unknown>(gamificationEndpoints.discoveryBackfill, {
      method: 'POST',
      body: { limit: 5, retry_failed: retryFailed },
    }))
  },
}
