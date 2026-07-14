import { describe, expect, it } from 'vitest'
import type { Activity } from '../../api'
import { groupActivitiesByWeek } from './useActivitiesViewModel'

function activity(id: string, startedAt: string): Activity {
  return {
    id, title: id, type: 'ride', notes: null, started_at: startedAt,
    distance_m: 1_000, duration_s: 300, moving_time_s: 280, elevation_gain_m: 20,
    avg_speed_mps: 4, max_speed_mps: 5, avg_hr_bpm: null, max_hr_bpm: null,
    avg_power_w: null, avg_cadence_rpm: null, training_load: null,
  }
}

describe('groupActivitiesByWeek', () => {
  it('gruppiert chronologisch gelieferte Aktivitäten nach Montag bis Sonntag', () => {
    const groups = groupActivitiesByWeek([
      activity('sonntag', '2026-07-19T08:00:00Z'),
      activity('montag', '2026-07-13T08:00:00Z'),
      activity('vorwoche', '2026-07-12T08:00:00Z'),
    ])
    expect(groups).toHaveLength(2)
    expect(groups[0].activities.map((item) => item.id)).toEqual(['sonntag', 'montag'])
    expect(groups[1].activities.map((item) => item.id)).toEqual(['vorwoche'])
  })
})
