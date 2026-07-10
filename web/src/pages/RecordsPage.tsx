import EmojiEventsRoundedIcon from '@mui/icons-material/EmojiEventsRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded'
import TimerRoundedIcon from '@mui/icons-material/TimerRounded'
import WorkspacePremiumRoundedIcon from '@mui/icons-material/WorkspacePremiumRounded'
import { alpha, Box, Button, Card, CardContent, Chip, Skeleton, Stack, Typography, useTheme } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { insightsApi, type ActivityRecord, type DistanceRecord } from '../api'
import { EmptyState, ErrorState } from '../components/States'
import { PageHeader } from '../components/PageHeader'
import { formatDate, formatDistance, formatDuration, formatSpeedMps } from '../utils/format'

export function RecordsPage() {
  const theme = useTheme()
  const records = useQuery({
    queryKey: ['statistics', 'records'],
    queryFn: insightsApi.records,
  })

  return (
    <>
      <PageHeader
        eyebrow="DEINE BESTLEISTUNGEN"
        title="Persönliche Rekorde"
        description="Deine schnellsten 10, 20, 30, 40 und 50 Kilometer sowie die längste und im Durchschnitt schnellste Tour."
      />

      {records.isError && <ErrorState error={records.error} onRetry={() => void records.refetch()} />}
      {records.isLoading && (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2 }}>
          {Array.from({ length: 7 }).map((_, index) => <Skeleton key={index} variant="rounded" height={index < 2 ? 220 : 180} />)}
        </Box>
      )}
      {records.data && (
        <>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 2, mb: 3 }}>
            <ActivityRecordCard
              title="Längste Tour"
              icon={<RouteRoundedIcon />}
              record={records.data.longest_ride}
              primaryValue={records.data.longest_ride ? formatDistance(records.data.longest_ride.distance_m) : '–'}
              secondaryValue={records.data.longest_ride ? formatDuration(records.data.longest_ride.moving_time_s) : undefined}
              accent={theme.palette.chart.blue}
            />
            <ActivityRecordCard
              title="Höchste Durchschnittsgeschwindigkeit"
              icon={<SpeedRoundedIcon />}
              record={records.data.highest_average_speed}
              primaryValue={records.data.highest_average_speed ? formatSpeedMps(records.data.highest_average_speed.avg_speed_mps) : '–'}
              secondaryValue={records.data.highest_average_speed ? formatDistance(records.data.highest_average_speed.distance_m) : undefined}
              accent={theme.palette.chart.amber}
            />
          </Box>

          <Stack direction="row" alignItems="center" gap={1} sx={{ mb: 1.5 }}>
            <WorkspacePremiumRoundedIcon color="primary" />
            <Box>
              <Typography variant="h3">Distanzrekorde</Typography>
              <Typography variant="body2" color="text.secondary">Schnellster zusammenhängender Abschnitt je Zieldistanz</Typography>
            </Box>
          </Stack>

          {records.data.distance_records.length > 0 ? (
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', xl: 'repeat(5, 1fr)' }, gap: 1.5 }}>
              {records.data.distance_records.map((record, index) => <DistanceRecordCard key={record.target_distance_m} record={record} rank={index + 1} />)}
            </Box>
          ) : (
            <Card><EmptyState title="Noch keine Distanzrekorde" description="Sobald eine Tour mindestens 10 Kilometer enthält, erscheint hier die erste Bestzeit." /></Card>
          )}

          {records.data.methods.length > 0 && (
            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h3">So werden Rekorde ermittelt</Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 1.5, mt: 1.5 }}>
                  {records.data.methods.map((method, index) => (
                    <Box key={`${method.name}-${index}`} sx={{ p: 1.5, borderRadius: 3, bgcolor: 'action.hover' }}>
                      <Typography fontWeight={750}>{method.name}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: .35 }}>{method.description}</Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </>
  )
}

function ActivityRecordCard({ title, icon, record, primaryValue, secondaryValue, accent }: { title: string; icon: React.ReactNode; record: ActivityRecord | null; primaryValue: string; secondaryValue?: string; accent: string }) {
  return (
    <Card sx={{ overflow: 'hidden', background: `linear-gradient(140deg, ${alpha(accent, .14)}, rgba(255,255,255,.96) 60%)` }}>
      <CardContent sx={{ p: { xs: 2.5, sm: 3 }, '&:last-child': { pb: { xs: 2.5, sm: 3 } } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
          <Box>
            <Typography variant="body2" color="text.secondary" fontWeight={700}>{title}</Typography>
            <Typography variant="h2" sx={{ fontSize: { xs: '2rem', md: '2.4rem' }, mt: 1 }}>{primaryValue}</Typography>
            {secondaryValue && <Typography color="text.secondary">{secondaryValue}</Typography>}
          </Box>
          <Box sx={{ width: 52, height: 52, borderRadius: 3.5, display: 'grid', placeItems: 'center', bgcolor: alpha(accent, .14), color: accent, '& svg': { fontSize: 30 } }}>{icon}</Box>
        </Stack>
        {record ? (
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', sm: 'center' }} gap={1} sx={{ mt: 2.5 }}>
            <Box sx={{ minWidth: 0 }}><Typography fontWeight={750} noWrap>{record.title}</Typography><Typography variant="caption" color="text.secondary">{formatDate(record.started_at)}</Typography></Box>
            <Button component={RouterLink} to={`/aktivitaeten/${record.activity_id}`} size="small">Fahrt öffnen</Button>
          </Stack>
        ) : <Typography color="text.secondary" sx={{ mt: 2.5 }}>Noch keine passende Aktivität vorhanden.</Typography>}
      </CardContent>
    </Card>
  )
}

function DistanceRecordCard({ record, rank }: { record: DistanceRecord; rank: number }) {
  const targetKm = record.target_distance_m / 1000
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" alignItems="center" gap={.75}>
            <EmojiEventsRoundedIcon color={rank === 1 ? 'secondary' : 'primary'} />
            <Typography variant="h3">{targetKm.toLocaleString('de-DE')} km</Typography>
          </Stack>
          {record.estimated && <Chip size="small" variant="outlined" label="interpoliert" />}
        </Stack>
        <Typography variant="h2" sx={{ fontSize: '1.8rem', mt: 2 }}>{formatDuration(record.duration_s)}</Typography>
        <Stack direction="row" alignItems="center" gap={.6} sx={{ mt: .5 }}><TimerRoundedIcon sx={{ fontSize: 17, color: 'text.secondary' }} /><Typography variant="body2" color="text.secondary">{formatSpeedMps(record.avg_speed_mps)} im Schnitt</Typography></Stack>
        <Typography fontWeight={750} noWrap sx={{ mt: 2 }}>{record.title}</Typography>
        <Typography variant="caption" color="text.secondary">{formatDate(record.started_at)} · {record.source}</Typography>
        <Button component={RouterLink} to={`/aktivitaeten/${record.activity_id}`} fullWidth sx={{ mt: 1.5 }}>Aktivität ansehen</Button>
      </CardContent>
    </Card>
  )
}
