import EmojiEventsRoundedIcon from '@mui/icons-material/EmojiEventsRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded'
import TimerRoundedIcon from '@mui/icons-material/TimerRounded'
import WorkspacePremiumRoundedIcon from '@mui/icons-material/WorkspacePremiumRounded'
import ShareRoundedIcon from '@mui/icons-material/ShareRounded'
import { alpha, Box, Button, Card, CardContent, Chip, IconButton, Skeleton, Stack, Tooltip, Typography, useTheme } from '@mui/material'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { insightsApi, type ActivityRecord, type DistanceRecord } from '../api'
import { EmptyState, ErrorState } from '../components/States'
import { PageHeader } from '../components/PageHeader'
import { formatDate, formatDistance, formatDuration, formatSpeedMps } from '../utils/format'
import { formatElevation } from '../utils/format'
import { AchievementShareDialog } from '../share/AchievementShareDialog'
import type { AchievementInfo } from '../share/types'

const recordMethodLabels: Record<string, string> = {
  distance_record_track_points: 'Trackbasierte Abschnittszeit',
  distance_record_fallback: 'Gekennzeichnete Schätzung',
}

export function RecordsPage() {
  const theme = useTheme()
  const [share, setShare] = useState<{ activityId: string; achievement: AchievementInfo } | null>(null)
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
              onShare={records.data.longest_ride ? () => setShare({ activityId: records.data.longest_ride!.activity_id, achievement: { kind: 'longest_ride', label: 'Längste Tour', value: formatDistance(records.data.longest_ride!.distance_m), detail: formatDuration(records.data.longest_ride!.moving_time_s) } }) : undefined}
            />
            <ActivityRecordCard
              title="Höchste Durchschnittsgeschwindigkeit"
              icon={<SpeedRoundedIcon />}
              record={records.data.highest_average_speed}
              primaryValue={records.data.highest_average_speed ? formatSpeedMps(records.data.highest_average_speed.avg_speed_mps) : '–'}
              secondaryValue={records.data.highest_average_speed ? formatDistance(records.data.highest_average_speed.distance_m) : undefined}
              accent={theme.palette.chart.amber}
              onShare={records.data.highest_average_speed ? () => setShare({ activityId: records.data.highest_average_speed!.activity_id, achievement: { kind: 'fastest_ride', label: 'Schnellste Tour', value: formatSpeedMps(records.data.highest_average_speed!.avg_speed_mps), detail: formatDistance(records.data.highest_average_speed!.distance_m) } }) : undefined}
            />
            <ActivityRecordCard
              title="Höchste Tour"
              icon={<WorkspacePremiumRoundedIcon />}
              record={records.data.highest_elevation_gain}
              primaryValue={records.data.highest_elevation_gain ? formatElevation(records.data.highest_elevation_gain.elevation_gain_m) : '–'}
              secondaryValue={records.data.highest_elevation_gain ? formatDistance(records.data.highest_elevation_gain.distance_m) : undefined}
              accent={theme.palette.chart.coral}
              onShare={records.data.highest_elevation_gain ? () => setShare({ activityId: records.data.highest_elevation_gain!.activity_id, achievement: { kind: 'elevation_record', label: 'Höhenmeter-Rekord', value: formatElevation(records.data.highest_elevation_gain!.elevation_gain_m), detail: formatDistance(records.data.highest_elevation_gain!.distance_m) } }) : undefined}
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
              {records.data.distance_records.map((record, index) => <DistanceRecordCard key={record.target_distance_m} record={record} rank={index + 1} onShare={() => setShare({ activityId: record.activity_id, achievement: { kind: 'distance_pr', label: `Bestzeit über ${(record.target_distance_m / 1000).toLocaleString('de-DE')} km`, value: formatDuration(record.duration_s), detail: formatSpeedMps(record.avg_speed_mps), segmentStartM: record.segment_start_m, segmentEndM: record.segment_end_m } })} />)}
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
                      <Typography fontWeight={750}>{recordMethodLabels[method.name] ?? method.name}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: .35 }}>{method.description}</Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      )}
      <AchievementShareDialog open={Boolean(share)} onClose={() => setShare(null)} activityId={share?.activityId ?? null} achievement={share?.achievement ?? null} />
    </>
  )
}

function ActivityRecordCard({ title, icon, record, primaryValue, secondaryValue, accent, onShare }: { title: string; icon: React.ReactNode; record: ActivityRecord | null; primaryValue: string; secondaryValue?: string; accent: string; onShare?: () => void }) {
  const theme = useTheme()
  return (
    <Card sx={{ overflow: 'hidden', background: `linear-gradient(140deg, ${alpha(accent, .14)}, ${theme.palette.background.paper} 60%)` }}>
      <CardContent sx={{ p: { xs: 2.5, sm: 3 }, '&:last-child': { pb: { xs: 2.5, sm: 3 } } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
          <Box>
            <Typography variant="body2" color="text.secondary" fontWeight={700}>{title}</Typography>
            <Typography variant="h2" sx={{ fontSize: { xs: '2rem', md: '2.4rem' }, mt: 1 }}>{primaryValue}</Typography>
            {secondaryValue && <Typography color="text.secondary">{secondaryValue}</Typography>}
          </Box>
          <Stack alignItems="flex-end" gap={1}><Box sx={{ width: 52, height: 52, borderRadius: 3.5, display: 'grid', placeItems: 'center', bgcolor: alpha(accent, .14), color: accent, '& svg': { fontSize: 30 } }}>{icon}</Box>{onShare && <Tooltip title="Rekord teilen"><IconButton aria-label={`${title} teilen`} onClick={onShare}><ShareRoundedIcon /></IconButton></Tooltip>}</Stack>
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

function DistanceRecordCard({ record, rank, onShare }: { record: DistanceRecord; rank: number; onShare: () => void }) {
  const targetKm = record.target_distance_m / 1000
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" alignItems="center" gap={.75}>
            <EmojiEventsRoundedIcon color={rank === 1 ? 'secondary' : 'primary'} />
            <Typography variant="h3">{targetKm.toLocaleString('de-DE')} km</Typography>
          </Stack>
          <Stack direction="row" alignItems="center">{record.estimated && <Chip size="small" variant="outlined" label="geschätzt" />}<Tooltip title="Bestzeit teilen"><IconButton aria-label={`${targetKm} km Bestzeit teilen`} onClick={onShare}><ShareRoundedIcon fontSize="small" /></IconButton></Tooltip></Stack>
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
