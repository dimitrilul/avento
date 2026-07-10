import { useState } from 'react'
import CompareArrowsRoundedIcon from '@mui/icons-material/CompareArrowsRounded'
import { Alert, Box, Button, Card, CardContent, Chip, Skeleton, Stack, Typography, useTheme } from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { activitiesApi, type Activity } from '../api'
import { ActivityCard } from '../components/ActivityCard'
import { EmptyState, ErrorState } from '../components/States'
import { PageHeader } from '../components/PageHeader'
import { errorMessage, formatDistance, formatDuration, formatElevation, formatSpeedMps } from '../utils/format'

export function ComparePage() {
  const [selected, setSelected] = useState<string[]>([])
  const theme = useTheme()
  const list = useQuery({ queryKey: ['activities', 'compare-picker'], queryFn: () => activitiesApi.list({ limit: 50 }) })
  const compare = useMutation({ mutationFn: activitiesApi.compare })
  function toggle(activity: Activity) { setSelected((current) => current.includes(activity.id) ? current.filter((id) => id !== activity.id) : current.length < 4 ? [...current, activity.id] : current) }
  const result = compare.data?.activities ?? []
  const chart = result.map((activity) => ({ name: activity.title, Distanz: activity.distance_m / 1000, Höhenmeter: activity.elevation_gain_m }))
  return <>
    <PageHeader eyebrow="SIDE BY SIDE" title="Fahrten vergleichen" description="Wähle zwei bis vier Aktivitäten und erkenne Unterschiede bei Strecke, Tempo und Belastung." />
    {list.isError && <ErrorState error={list.error} onRetry={() => void list.refetch()} />}
    {list.isLoading && <Skeleton variant="rounded" height={320} />}
    {list.data?.items.length === 0 && <EmptyState title="Keine Fahrten zum Vergleichen" description="Importiere mindestens zwei Aktivitäten." />}
    {list.data && list.data.items.length > 0 && <>
      <Stack direction="row" alignItems="center" justifyContent="space-between" gap={2} sx={{ mb: 2 }}><Stack direction="row" gap={1} alignItems="center"><Chip color="primary" label={`${selected.length} ausgewählt`} /><Typography variant="body2" color="text.secondary">maximal 4</Typography></Stack><Button variant="contained" startIcon={<CompareArrowsRoundedIcon />} disabled={selected.length < 2 || compare.isPending} onClick={() => compare.mutate(selected)}>{compare.isPending ? 'Wird verglichen …' : 'Vergleich anzeigen'}</Button></Stack>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2, maxHeight: result.length ? 420 : 'none', overflow: result.length ? 'auto' : 'visible', pr: result.length ? 1 : 0 }}>{list.data.items.map((activity) => <ActivityCard key={activity.id} activity={activity} selected={selected.includes(activity.id)} onSelect={toggle} />)}</Box>
    </>}
    {selected.length === 4 && !compare.data && <Alert severity="info" sx={{ mt: 2 }}>Vier Fahrten ausgewählt. Entferne eine, um eine andere hinzuzufügen.</Alert>}
    {compare.isError && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage(compare.error)}</Alert>}
    {result.length > 0 && <Box sx={{ mt: 4 }}><Typography variant="h3" sx={{ mb: 2 }}>Ergebnis</Typography><Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1.2fr 1fr' }, gap: 2.5 }}><Card><CardContent><ResponsiveContainer width="100%" height={330}><BarChart data={chart}><CartesianGrid vertical={false} strokeDasharray="4 4" stroke={theme.palette.divider} /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip /><Legend /><Bar dataKey="Distanz" unit=" km" fill={theme.palette.chart.teal} radius={[6,6,0,0]} /><Bar dataKey="Höhenmeter" unit=" m" fill={theme.palette.chart.lime} radius={[6,6,0,0]} /></BarChart></ResponsiveContainer></CardContent></Card><Card><CardContent><Stack spacing={2}>{result.map((activity) => <Box key={activity.id} sx={{ pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}><Typography fontWeight={800}>{activity.title}</Typography><Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1 }}><Chip label={formatDistance(activity.distance_m)} /><Chip label={formatDuration(activity.moving_time_s)} /><Chip label={formatElevation(activity.elevation_gain_m)} /><Chip label={formatSpeedMps(activity.avg_speed_mps)} /></Stack></Box>)}</Stack></CardContent></Card></Box></Box>}
  </>
}
