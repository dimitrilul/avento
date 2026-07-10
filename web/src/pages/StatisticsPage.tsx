import { useMemo, useState } from 'react'
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded'
import CalendarMonthRoundedIcon from '@mui/icons-material/CalendarMonthRounded'
import DirectionsBikeRoundedIcon from '@mui/icons-material/DirectionsBikeRounded'
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded'
import TimerRoundedIcon from '@mui/icons-material/TimerRounded'
import { Box, Button, Card, CardContent, Chip, Skeleton, Stack, TextField, Typography, useTheme } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { statisticsApi, type StatisticsGranularity } from '../api'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { EmptyState, ErrorState } from '../components/States'
import { formatDistance, formatDuration, formatElevation, formatHeartRate, formatSpeedMps } from '../utils/format'

type PresetId = 'last_week' | 'four_weeks' | 'last_month' | 'last_quarter' | 'year' | 'custom'

interface DateRange {
  from: string
  to: string
}

const presets: Array<{ id: PresetId; label: string }> = [
  { id: 'last_week', label: 'Letzte Woche' },
  { id: 'four_weeks', label: 'Letzte 4 Wochen' },
  { id: 'last_month', label: 'Letzter Monat' },
  { id: 'last_quarter', label: 'Letztes Quartal' },
  { id: 'year', label: 'Dieses Jahr' },
  { id: 'custom', label: 'Benutzerdefiniert' },
]

function dateInput(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function startOfWeek(value: Date) {
  const result = new Date(value)
  result.setHours(12, 0, 0, 0)
  result.setDate(result.getDate() - ((result.getDay() + 6) % 7))
  return result
}

function rangeForPreset(preset: Exclude<PresetId, 'custom'>, today = new Date()): DateRange {
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
    const currentQuarter = Math.floor(current.getMonth() / 3)
    const from = new Date(current.getFullYear(), (currentQuarter - 1) * 3, 1, 12)
    const to = new Date(from.getFullYear(), from.getMonth() + 3, 0, 12)
    return { from: dateInput(from), to: dateInput(to) }
  }
  return { from: `${current.getFullYear()}-01-01`, to: dateInput(current) }
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${value}T12:00:00`))
}

function chartLabel(value: string, granularity: StatisticsGranularity) {
  const normalized = value.length === 7 ? `${value}-01` : value.slice(0, 10)
  const date = new Date(`${normalized}T12:00:00`)
  if (granularity === 'month') return new Intl.DateTimeFormat('de-DE', { month: 'short', year: '2-digit' }).format(date)
  if (granularity === 'week') return `ab ${new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(date)}`
  return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' }).format(date)
}

const granularityLabels: Record<StatisticsGranularity, string> = {
  auto: 'automatisch',
  day: 'täglich',
  week: 'wöchentlich',
  month: 'monatlich',
}

export function StatisticsPage() {
  const theme = useTheme()
  const initialRange = useMemo(() => rangeForPreset('four_weeks'), [])
  const [preset, setPreset] = useState<PresetId>('four_weeks')
  const [range, setRange] = useState<DateRange>(initialRange)
  const rangeIsValid = Boolean(range.from && range.to && range.from <= range.to)
  const query = useQuery({
    queryKey: ['statistics', 'overview', range.from, range.to, 'auto'],
    queryFn: () => statisticsApi.overview(range.from, range.to, 'auto'),
    enabled: rangeIsValid,
  })

  function selectPreset(next: PresetId) {
    setPreset(next)
    if (next !== 'custom') setRange(rangeForPreset(next))
  }

  const data = query.data
  const comparison = data?.comparison
  const change = (...keys: string[]) => {
    for (const key of keys) {
      const value = comparison?.changes[key]
      if (value !== undefined) return value
    }
    return null
  }
  const series = (data?.series ?? []).map((point) => ({
    ...point,
    label: chartLabel(point.period_start, data?.granularity ?? 'day'),
    distanceKm: point.distance_m / 1000,
    durationHours: point.duration_s / 3600,
    movingHours: point.moving_time_s / 3600,
    pauseHours: Math.max(0, point.duration_s - point.moving_time_s) / 3600,
    speedKmh: point.avg_speed_mps == null ? null : point.avg_speed_mps * 3.6,
  }))
  const tooltipStyle = { borderRadius: 14, border: `1px solid ${theme.palette.divider}`, boxShadow: '0 12px 30px rgba(20,50,45,.08)' }
  const comparisonHint = comparison ? `gegen ${displayDate(comparison.date_from)} – ${displayDate(comparison.date_to)}` : 'im gewählten Zeitraum'

  return (
    <>
      <PageHeader
        eyebrow="FORTSCHRITT"
        title="Statistiken"
        description="Verfolge Umfang, Konstanz und Belastung über jeden beliebigen Zeitraum – inklusive direktem Vergleich mit der Vorperiode."
      />

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: { xs: 2, md: 2.5 }, '&:last-child': { pb: { xs: 2, md: 2.5 } } }}>
          <Stack direction="row" gap={1} flexWrap="wrap">
            {presets.map((item) => (
              <Button key={item.id} variant={preset === item.id ? 'contained' : 'outlined'} color={preset === item.id ? 'primary' : 'inherit'} onClick={() => selectPreset(item.id)}>
                {item.label}
              </Button>
            ))}
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ xs: 'stretch', sm: 'center' }} gap={1.5} sx={{ mt: 2 }}>
            <TextField label="Von" type="date" value={range.from} onChange={(event) => { setPreset('custom'); setRange((current) => ({ ...current, from: event.target.value })) }} slotProps={{ inputLabel: { shrink: true } }} />
            <TextField label="Bis" type="date" value={range.to} onChange={(event) => { setPreset('custom'); setRange((current) => ({ ...current, to: event.target.value })) }} slotProps={{ inputLabel: { shrink: true } }} />
            {rangeIsValid ? (
              <Stack direction="row" alignItems="center" gap={1} sx={{ ml: { sm: 'auto' } }}>
                <CalendarMonthRoundedIcon color="action" />
                <Typography variant="body2" color="text.secondary">{displayDate(range.from)} – {displayDate(range.to)}</Typography>
                {data?.granularity && <Chip size="small" label={granularityLabels[data.granularity]} />}
              </Stack>
            ) : <Typography color="error.main" variant="body2">Das Startdatum muss vor dem Enddatum liegen.</Typography>}
          </Stack>
        </CardContent>
      </Card>

      {query.isError && <ErrorState error={query.error} onRetry={() => void query.refetch()} />}
      {query.isLoading && <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', lg: 'repeat(4, 1fr)' }, gap: 2 }}>{Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} variant="rounded" height={145} />)}</Box>}
      {data && (
        <>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', lg: 'repeat(4, 1fr)' }, gap: 2, mb: 3 }}>
            <MetricCard label="Fahrten" value={String(data.activity_count)} icon={<DirectionsBikeRoundedIcon />} accent={theme.palette.chart.teal} delta={change('activity_count', 'activities')} hint={comparisonHint} />
            <MetricCard label="Distanz" value={formatDistance(data.distance_m)} icon={<RouteRoundedIcon />} accent={theme.palette.chart.blue} delta={change('distance_m')} hint={comparisonHint} />
            <MetricCard label="Gesamtzeit" value={formatDuration(data.duration_s)} icon={<AccessTimeRoundedIcon />} accent={theme.palette.chart.amber} delta={change('duration_s')} hint={comparisonHint} />
            <MetricCard label="Bewegungszeit" value={formatDuration(data.moving_time_s)} icon={<TimerRoundedIcon />} accent={theme.palette.chart.teal} delta={change('moving_time_s')} hint={comparisonHint} />
            <MetricCard label="Höhenmeter" value={formatElevation(data.elevation_gain_m)} icon={<LandscapeRoundedIcon />} accent={theme.palette.chart.coral} delta={change('elevation_gain_m')} hint={comparisonHint} />
            <MetricCard label="Ø Geschwindigkeit" value={formatSpeedMps(data.avg_speed_mps)} icon={<SpeedRoundedIcon />} accent={theme.palette.chart.lime} delta={change('avg_speed_mps')} hint={comparisonHint} />
            <MetricCard label="Ø Herzfrequenz" value={formatHeartRate(data.avg_hr_bpm)} icon={<FavoriteRoundedIcon />} accent={theme.palette.chart.coral} delta={change('avg_hr_bpm')} hint={comparisonHint} />
            <MetricCard label="Trainingsbelastung" value={Math.round(data.training_load ?? 0).toLocaleString('de-DE')} icon={<DirectionsBikeRoundedIcon />} accent={theme.palette.chart.amber} delta={change('training_load')} hint={comparisonHint} />
          </Box>

          {series.length ? (
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2.5 }}>
              <ChartCard title="Distanz & Fahrten" subtitle="Trainingsumfang und Häufigkeit">
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={series} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} strokeDasharray="4 4" stroke={theme.palette.divider} />
                    <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="distance" unit=" km" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="count" orientation="right" allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend />
                    <Bar yAxisId="distance" dataKey="distanceKm" name="Distanz (km)" fill={theme.palette.chart.teal} radius={[6, 6, 0, 0]} />
                    <Line yAxisId="count" type="monotone" dataKey="activity_count" name="Fahrten" stroke={theme.palette.chart.coral} strokeWidth={3} dot={{ r: 3 }} connectNulls />
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Zeit & Höhenmeter" subtitle="Bewegung, Pausen und Anstieg">
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={series} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} strokeDasharray="4 4" stroke={theme.palette.divider} />
                    <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="time" unit=" h" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="elevation" orientation="right" unit=" m" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend />
                    <Bar yAxisId="time" stackId="time" dataKey="movingHours" name="Bewegung (Std.)" fill={theme.palette.chart.blue} radius={[0, 0, 0, 0]} />
                    <Bar yAxisId="time" stackId="time" dataKey="pauseHours" name="Pausen (Std.)" fill={theme.palette.chart.amber} radius={[6, 6, 0, 0]} />
                    <Line yAxisId="elevation" type="monotone" dataKey="elevation_gain_m" name="Höhenmeter" stroke={theme.palette.chart.lime} strokeWidth={3} dot={false} connectNulls />
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Tempo & Herzfrequenz" subtitle="Leistungsentwicklung bei vergleichbarer Belastung" fullWidth>
                <ResponsiveContainer width="100%" height={310}>
                  <ComposedChart data={series} margin={{ top: 10, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid vertical={false} strokeDasharray="4 4" stroke={theme.palette.divider} />
                    <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="speed" unit=" km/h" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="heart" orientation="right" unit=" bpm" domain={['auto', 'auto']} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Legend />
                    <Line yAxisId="speed" type="monotone" dataKey="speedKmh" name="Ø Geschwindigkeit" stroke={theme.palette.chart.teal} strokeWidth={3} dot={{ r: 3 }} connectNulls />
                    <Line yAxisId="heart" type="monotone" dataKey="avg_hr_bpm" name="Ø Herzfrequenz" stroke={theme.palette.chart.coral} strokeWidth={3} dot={{ r: 3 }} connectNulls />
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartCard>
            </Box>
          ) : <Card><EmptyState title="Noch keine Statistik" description="Für den gewählten Zeitraum wurden keine Aktivitäten gefunden." /></Card>}
        </>
      )}
    </>
  )
}

function ChartCard({ title, subtitle, fullWidth, children }: { title: string; subtitle: string; fullWidth?: boolean; children: React.ReactNode }) {
  return (
    <Card sx={fullWidth ? { gridColumn: { xl: '1 / -1' } } : undefined}>
      <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Typography variant="h3">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{subtitle}</Typography>
        {children}
      </CardContent>
    </Card>
  )
}
