import { useDeferredValue, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { activitiesApi, type Activity, type ActivityFilters } from '../../api'

export const activitiesPageSize = 12

export type ActivityWeek = {
  key: string
  label: string
  activities: Activity[]
}

function validPage(value: string | null) {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1
}

function weekStart(value: string) {
  const date = new Date(value)
  const day = date.getDay() || 7
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() - day + 1)
  return date
}

export function groupActivitiesByWeek(activities: Activity[]): ActivityWeek[] {
  const formatter = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'long' })
  const groups = new Map<string, ActivityWeek>()
  for (const activity of activities) {
    const start = weekStart(activity.started_at)
    const end = new Date(start)
    end.setDate(end.getDate() + 6)
    const key = start.toISOString().slice(0, 10)
    const existing = groups.get(key)
    if (existing) existing.activities.push(activity)
    else groups.set(key, {
      key,
      label: `${formatter.format(start)} – ${formatter.format(end)}`,
      activities: [activity],
    })
  }
  return [...groups.values()]
}

export function useActivitiesViewModel() {
  const [params, setParams] = useSearchParams()
  const search = params.get('q') ?? ''
  const deferredSearch = useDeferredValue(search)
  const type = params.get('type') ?? ''
  const dateFrom = params.get('date_from') ?? ''
  const dateTo = params.get('date_to') ?? ''
  const page = validPage(params.get('page'))
  const filters: ActivityFilters = {
    q: deferredSearch.trim() || undefined,
    type: type || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    limit: activitiesPageSize,
    offset: (page - 1) * activitiesPageSize,
  }
  const query = useQuery({ queryKey: ['activities', filters], queryFn: () => activitiesApi.list(filters) })
  const groups = useMemo(() => groupActivitiesByWeek(query.data?.items ?? []), [query.data?.items])
  const hasFilters = Boolean(search || type || dateFrom || dateTo)

  function update(name: 'q' | 'type' | 'date_from' | 'date_to' | 'page', value: string) {
    setParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set(name, value)
      else next.delete(name)
      if (name !== 'page') next.delete('page')
      return next
    }, { replace: true })
  }

  function reset() {
    setParams(new URLSearchParams(), { replace: true })
  }

  return { query, groups, search, type, dateFrom, dateTo, page, hasFilters, update, reset }
}
