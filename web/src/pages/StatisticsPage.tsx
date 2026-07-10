import { useState } from 'react'
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded'
import DirectionsBikeRoundedIcon from '@mui/icons-material/DirectionsBikeRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import { Box, Card, CardContent, MenuItem, Skeleton, Stack, TextField, Typography, useTheme } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { statisticsApi } from '../api'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { EmptyState, ErrorState } from '../components/States'
import { TrendChart } from '../components/TrendChart'
import { formatDistance, formatDuration, formatElevation } from '../utils/format'

export function StatisticsPage() {
  const [year, setYear] = useState(String(new Date().getFullYear()))
  const theme = useTheme()
  const query = useQuery({ queryKey: ['statistics', 'overview', year], queryFn: () => statisticsApi.overview(`${year}-01-01`, `${year}-12-31`) })
  const years = Array.from({ length: 5 }, (_, index) => String(new Date().getFullYear() - index))
  const chart = (query.data?.by_month ?? []).map((point) => ({ ...point, label: new Intl.DateTimeFormat('de-DE', { month: 'short' }).format(new Date(`${point.month}-01T12:00:00`)), hours: point.duration_s / 3600 }))
  return <>
    <PageHeader eyebrow="FORTSCHRITT" title="Statistiken" description="Erkenne Umfang, Konstanz und Belastung in deinem Radjahr." action={<TextField select label="Jahr" value={year} onChange={(event) => setYear(event.target.value)} sx={{ minWidth: 130 }}>{years.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}</TextField>} />
    {query.isError && <ErrorState error={query.error} onRetry={() => void query.refetch()} />}
    {query.isLoading ? <Skeleton variant="rounded" height={150} /> : query.data && <>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', lg: 'repeat(4, 1fr)' }, gap: 2, mb: 3 }}>
        <MetricCard label="Aktivitäten" value={String(query.data.activity_count)} icon={<DirectionsBikeRoundedIcon />} accent={theme.palette.chart.teal} />
        <MetricCard label="Distanz" value={formatDistance(query.data.distance_m)} icon={<RouteRoundedIcon />} accent={theme.palette.chart.blue} />
        <MetricCard label="Fahrzeit" value={formatDuration(query.data.moving_time_s)} icon={<AccessTimeRoundedIcon />} accent={theme.palette.chart.amber} />
        <MetricCard label="Höhenmeter" value={formatElevation(query.data.elevation_gain_m)} icon={<LandscapeRoundedIcon />} accent={theme.palette.chart.coral} />
      </Box>
      {chart.length ? <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2.5 }}>
        <Card><CardContent><Typography variant="h3">Distanz nach Monat</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Gefahrene Kilometer</Typography><TrendChart data={query.data.by_month} /></CardContent></Card>
        <Card><CardContent><Typography variant="h3">Umfang & Höhenmeter</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Aktive Stunden und Anstieg</Typography><ResponsiveContainer width="100%" height={290}><BarChart data={chart} margin={{ left: -10 }}><CartesianGrid vertical={false} strokeDasharray="4 4" stroke={theme.palette.divider} /><XAxis dataKey="label" axisLine={false} tickLine={false} /><YAxis yAxisId="hours" axisLine={false} tickLine={false} /><YAxis yAxisId="elevation" orientation="right" axisLine={false} tickLine={false} /><Tooltip /><Legend /><Bar yAxisId="hours" dataKey="hours" name="Zeit (Std.)" fill={theme.palette.chart.teal} radius={[6, 6, 0, 0]} /><Bar yAxisId="elevation" dataKey="elevation_gain_m" name="Höhe (m)" fill={theme.palette.chart.lime} radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></CardContent></Card>
      </Box> : <EmptyState title="Noch keine Statistik" description={`Für ${year} wurden noch keine Aktivitäten importiert.`} />}
    </>}
  </>
}
