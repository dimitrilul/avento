import { useEffect, useMemo } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { activitiesApi, insightsApi, statisticsApi, type Activity, type ActivityType, type StatisticsGranularity } from '../../api'

export type StatisticsPreset = 'last_week' | 'four_weeks' | 'last_month' | 'last_quarter' | 'year' | 'custom'
export type DevelopmentSeason = 'year' | 'spring' | 'summer' | 'autumn' | 'winter'

const activityTypes: ActivityType[] = ['ride', 'training', 'tour', 'commute', 'indoor', 'other']
const presets: StatisticsPreset[] = ['last_week', 'four_weeks', 'last_month', 'last_quarter', 'year', 'custom']
const seasons: DevelopmentSeason[] = ['year', 'spring', 'summer', 'autumn', 'winter']

function dateInput(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

function validDate(value: string | null) {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null
}

function startOfWeek(value: Date) {
  const result = new Date(value)
  result.setHours(12, 0, 0, 0)
  result.setDate(result.getDate() - ((result.getDay() + 6) % 7))
  return result
}

export function rangeForStatisticsPreset(preset: Exclude<StatisticsPreset, 'custom'>, today = new Date()) {
  const current = new Date(today)
  current.setHours(12, 0, 0, 0)
  if (preset === 'last_week') {
    const to = startOfWeek(current)
    to.setDate(to.getDate() - 1)
    const from = new Date(to)
    from.setDate(from.getDate() - 6)
    return { from: dateInput(from), to: dateInput(to) }
  }
  if (preset === 'four_weeks') {
    const from = new Date(current)
    from.setDate(from.getDate() - 27)
    return { from: dateInput(from), to: dateInput(current) }
  }
  if (preset === 'last_month') {
    const from = new Date(current.getFullYear(), current.getMonth() - 1, 1, 12)
    const to = new Date(current.getFullYear(), current.getMonth(), 0, 12)
    return { from: dateInput(from), to: dateInput(to) }
  }
  if (preset === 'last_quarter') {
    const quarter = Math.floor(current.getMonth() / 3)
    const from = new Date(current.getFullYear(), (quarter - 1) * 3, 1, 12)
    const to = new Date(from.getFullYear(), from.getMonth() + 3, 0, 12)
    return { from: dateInput(from), to: dateInput(to) }
  }
  return { from: `${current.getFullYear()}-01-01`, to: dateInput(current) }
}

export function useStatisticsViewModel() {
  const [params, setParams] = useSearchParams()
  const rawPreset = params.get('preset') as StatisticsPreset | null
  const preset = rawPreset && presets.includes(rawPreset) ? rawPreset : 'four_weeks'
  const fallback = useMemo(() => rangeForStatisticsPreset(preset === 'custom' ? 'four_weeks' : preset), [preset])
  const from = validDate(params.get('date_from')) ?? fallback.from
  const to = validDate(params.get('date_to')) ?? fallback.to
  const rawType = params.get('type') as ActivityType | null
  const type = rawType && activityTypes.includes(rawType) ? rawType : 'all'
  const rangeIsValid = from <= to
  const query = useQuery({
    queryKey: ['statistics', 'overview', from, to, 'auto', type],
    queryFn: () => statisticsApi.overview(from, to, 'auto', type === 'all' ? undefined : type),
    enabled: rangeIsValid,
  })
  const update = (values: { preset?: StatisticsPreset; from?: string; to?: string; type?: ActivityType | 'all' }) => {
    const next = new URLSearchParams(params)
    if (values.preset) {
      next.set('preset', values.preset)
      if (values.preset !== 'custom') {
        const range = rangeForStatisticsPreset(values.preset)
        next.set('date_from', range.from)
        next.set('date_to', range.to)
      }
    }
    if (values.from != null) next.set('date_from', values.from)
    if (values.to != null) next.set('date_to', values.to)
    if (values.type === 'all') next.delete('type')
    else if (values.type) next.set('type', values.type)
    setParams(next, { replace: true })
  }
  return { preset, from, to, type, rangeIsValid, query, update }
}

export function useDevelopmentViewModel() {
  const [params, setParams] = useSearchParams()
  const currentYear = new Date().getFullYear()
  const parsedYears = Number(params.get('years'))
  const years = [1, 3, 5].includes(parsedYears) ? parsedYears : 3
  const parsedReviewYear = Number(params.get('review_year'))
  const reviewYear = Number.isInteger(parsedReviewYear) && parsedReviewYear >= currentYear - 9 && parsedReviewYear <= currentYear ? parsedReviewYear : currentYear
  const rawSeason = params.get('season') as DevelopmentSeason | null
  const season = rawSeason && seasons.includes(rawSeason) ? rawSeason : 'year'
  const range = { from: `${currentYear - years + 1}-01-01`, to: dateInput(new Date()) }
  const insights = useQuery({ queryKey: ['statistics', 'insights', range.from, range.to], queryFn: () => insightsApi.longTerm(range.from, range.to) })
  const review = useQuery({ queryKey: ['statistics', 'review', reviewYear, season], queryFn: () => insightsApi.periodReview(reviewYear, season) })
  const update = (values: { years?: number; reviewYear?: number; season?: DevelopmentSeason }) => {
    const next = new URLSearchParams(params)
    if (values.years) next.set('years', String(values.years))
    if (values.reviewYear) next.set('review_year', String(values.reviewYear))
    if (values.season) next.set('season', values.season)
    setParams(next, { replace: true })
  }
  return { currentYear, years, reviewYear, season, range, insights, review, update }
}

export function useComparisonViewModel() {
  const [params, setParams] = useSearchParams()
  const selected = [...new Set(params.getAll('activity').filter(Boolean))].slice(0, 4)
  const list = useQuery({ queryKey: ['activities', 'compare-picker'], queryFn: () => activitiesApi.list({ limit: 50 }) })
  const compare = useMutation({ mutationFn: activitiesApi.compare })
  const selectionKey = selected.join('|')
  useEffect(() => {
    if (selected.length >= 2) compare.mutate(selected)
    else compare.reset()
    // selectionKey represents the complete URL selection and deliberately drives the comparison.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectionKey])
  const toggle = (activity: Activity) => {
    const nextSelection = selected.includes(activity.id) ? selected.filter((id) => id !== activity.id) : selected.length < 4 ? [...selected, activity.id] : selected
    const next = new URLSearchParams(params)
    next.delete('activity')
    nextSelection.forEach((id) => next.append('activity', id))
    setParams(next, { replace: true })
  }
  return { selected, list, compare, toggle }
}

export function useRecordsViewModel() {
  return useQuery({ queryKey: ['statistics', 'records'], queryFn: insightsApi.records })
}

export function analyticsChartLabel(value: string, granularity: StatisticsGranularity) {
  const normalized = value.length === 7 ? `${value}-01` : value.slice(0, 10)
  const date = new Date(`${normalized}T12:00:00`)
  if (granularity === 'month') return new Intl.DateTimeFormat('de-DE', { month: 'short', year: '2-digit' }).format(date)
  if (granularity === 'week') return `ab ${new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(date)}`
  return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(date)
}
