import { describe, expect, it, vi } from 'vitest'
import { gamificationApi, gamificationEndpoints, normalizeGamificationOverview } from './gamification'

function jsonResponse(value: unknown) {
  return new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } })
}

describe('Gamification-API', () => {
  it('normalisiert den Backend-Vertrag in ein stabiles UI-Modell', () => {
    const overview = normalizeGamificationOverview({
      generated_at: '2026-07-11T10:00:00Z',
      privacy: 'private',
      level: {
        level: 4,
        name: 'Pfadfinder:in',
        total_xp: 870,
        current_xp: 170,
        next_level_xp: 300,
        progress_percent: 56.7,
        breakdown: { goals: 250, badges: 620 },
      },
      goals: [{
        id: 'goal-1',
        title: '100 km im Monat',
        description: 'Ruhig über den Monat verteilt',
        metric: 'distance_m',
        current_value: 62_000,
        target_value: 100_000,
        unit: 'km',
        period: 'month',
        progress_percent: 62,
        remaining_value: 38_000,
        status: 'active',
        reward_xp: 80,
      }],
      active_challenges: [],
      challenge_suggestions: [{
        id: 'challenge-1',
        title: 'Morgenrunde',
        metric: 'activity_count',
        target_value: 2,
        reward_xp: 35,
        source: 'ai',
        weather_sensitive: true,
      }],
      ai_challenges_available: true,
      badges: [{ id: 'badge-1', key: 'first-ride', name: 'Erste Fahrt', unlocked: true, current_value: 1, target_value: 1 }],
      streak: { current_weeks: 3, best_weeks: 5, weekly_target: 2, current_week_progress: 1, pause_protection_available: true, method: 'calendar_week' },
      record_chases: [],
      discoveries: [
        { scope: 'city', label: 'Städte', count: 2, places: ['Freiburg', 'Lörrach'] },
        { scope: 'municipality', label: 'Kommunen', count: 1, places: ['Gundelfingen'] },
      ],
      geocoding: { status: 'ready', provider: 'locationiq', attribution_label: 'Search by LocationIQ.com', attribution_url: 'https://locationiq.com/attribution' },
      annual_awards: [{ id: 'award-1', key: 'distance', year: 2026, title: 'Weitblick', earned: true, reward_xp: 100, is_final: false }],
    })

    expect(overview.privacy).toBe('private')
    expect(overview.level.breakdown).toEqual({ goals: 250, badges: 620 })
    expect(overview.goals[0]).toMatchObject({ description: 'Ruhig über den Monat verteilt', remaining_value: 38_000, reward_xp: 80 })
    expect(overview.challenge_suggestions[0]).toMatchObject({ ai_generated: true, weather_sensitive: true, status: 'suggested' })
    expect(overview.discoveries).toEqual([
      expect.objectContaining({ scope: 'municipality', count: 3, places: ['Freiburg', 'Lörrach', 'Gundelfingen'] }),
    ])
    expect(overview.geocoding).toMatchObject({ status: 'ready', provider: 'locationiq' })
    expect(overview.annual_awards[0]).toMatchObject({ key: 'distance', reward_xp: 100, is_final: false })
  })

  it('hält alle mutierenden Pfade und Payloads im zentralen Vertrag', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (init?.method === 'DELETE' || url.endsWith('/decline')) return new Response(null, { status: 204 })
      if (url === '/api/v1/gamification/overview') return jsonResponse({})
      if (url === '/api/v1/gamification/discoveries/backfill') return jsonResponse({ processed: 1, available: 1, failed: 0, remaining: 0, total: 1 })
      return jsonResponse({ id: 'goal-1', title: 'Monatsziel', metric: 'distance_m', target_value: 80_000 })
    })

    await gamificationApi.overview()
    await gamificationApi.createGoal({ title: '  Monatsziel  ', metric: 'distance_m', target_value: 80_000, period: 'month', deadline: null })
    await gamificationApi.updateGoal('ziel/1', { title: 'Neuer Name' })
    await gamificationApi.deleteGoal('ziel/1')
    await gamificationApi.acceptChallenge('challenge/1')
    await gamificationApi.declineChallenge('challenge/1')
    await gamificationApi.backfillDiscoveries()

    expect(fetchMock.mock.calls.map(([url, init]) => [url, init?.method ?? 'GET'])).toEqual([
      ['/api/v1/gamification/overview', 'GET'],
      ['/api/v1/gamification/goals', 'POST'],
      ['/api/v1/gamification/goals/ziel%2F1', 'PATCH'],
      ['/api/v1/gamification/goals/ziel%2F1', 'DELETE'],
      ['/api/v1/gamification/challenges/challenge%2F1/accept', 'POST'],
      ['/api/v1/gamification/challenges/challenge%2F1/decline', 'POST'],
      ['/api/v1/gamification/discoveries/backfill', 'POST'],
    ])
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      title: 'Monatsziel',
      metric: 'distance_m',
      target_value: 80_000,
      period: 'month',
      deadline: null,
    })
    expect(JSON.parse(String(fetchMock.mock.calls[2][1]?.body))).toEqual({ title: 'Neuer Name' })
    expect(JSON.parse(String(fetchMock.mock.calls[6][1]?.body))).toEqual({ limit: 5, retry_failed: false })
    expect(gamificationEndpoints.overview).toBe('/gamification/overview')
  })
})
