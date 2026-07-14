import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { activitiesApi, gamificationApi, gamificationOverviewQueryKey, insightsApi } from '../../api'
import type { GamificationBadge } from '../../api'

export function badgesForActivity(badges: GamificationBadge[], activityId: string) {
  return badges.filter((badge) => badge.unlocked && badge.source_activity_id === activityId)
}

export function useActivityDetailViewModel() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const activity = useQuery({ queryKey: ['activity', id], queryFn: () => activitiesApi.get(id), enabled: Boolean(id) })
  const track = useQuery({ queryKey: ['activity', id, 'track'], queryFn: () => activitiesApi.track(id), enabled: Boolean(id) })
  const records = useQuery({ queryKey: ['statistics', 'records'], queryFn: insightsApi.records, enabled: Boolean(id) })
  const gamification = useQuery({ queryKey: gamificationOverviewQueryKey, queryFn: gamificationApi.overview, enabled: Boolean(id) })
  const remove = useMutation({
    mutationFn: () => activitiesApi.delete(id),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['activities'] }),
        client.invalidateQueries({ queryKey: ['statistics'] }),
      ])
      navigate('/aktivitaeten', { replace: true })
    },
  })
  const reanalyze = useMutation({
    mutationFn: () => activitiesApi.reanalyze(id),
    onSuccess: async (updated) => {
      client.setQueryData(['activity', id], updated)
      await Promise.all([
        client.invalidateQueries({ queryKey: ['activity', id, 'track'] }),
        client.invalidateQueries({ queryKey: ['activity', id, 'summary'] }),
        client.invalidateQueries({ queryKey: ['activities'] }),
        client.invalidateQueries({ queryKey: ['statistics'] }),
      ])
    },
  })
  const activityBadges = badgesForActivity(gamification.data?.badges ?? [], id)
  return { id, activity, track, records, gamification, activityBadges, remove, reanalyze }
}
