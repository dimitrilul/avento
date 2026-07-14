import { describe, expect, it } from 'vitest'
import type { GamificationBadge } from '../../api'
import { badgesForActivity } from './useActivityDetailViewModel'

function badge(id: string, activityId: string | null, unlocked = true): GamificationBadge {
  return { id, key: id, name: id, description: id, category: 'distance', tier: 'bronze', icon: null, reward_xp: 10, unlocked, unlocked_at: null, source_activity_id: activityId, current_value: 1, target_value: 1, unit: 'km', progress_percent: 100 }
}

describe('badgesForActivity', () => {
  it('zeigt nur tatsächlich durch diese Aktivität freigeschaltete Badges', () => {
    expect(badgesForActivity([
      badge('passend', 'activity-1'),
      badge('andere-aktivitaet', 'activity-2'),
      badge('noch-gesperrt', 'activity-1', false),
      badge('ohne-quelle', null),
    ], 'activity-1').map((item) => item.id)).toEqual(['passend'])
  })
})
