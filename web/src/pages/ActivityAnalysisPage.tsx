import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded'
import { Box, Button, Chip, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useParams } from 'react-router-dom'
import { activitiesApi } from '../api'
import { AdvancedActivityAnalysis } from '../components/AdvancedActivityAnalysis'
import { ContentLoading, ErrorState } from '../components/States'
import {
  activityTypeLabels,
  formatDateTime,
  formatDistance,
  formatDuration,
  formatElevation,
} from '../utils/format'

export function ActivityAnalysisPage() {
  const { id = '' } = useParams()
  const activity = useQuery({
    queryKey: ['activity', id],
    queryFn: () => activitiesApi.get(id),
    enabled: Boolean(id),
  })
  const track = useQuery({
    queryKey: ['activity', id, 'track'],
    queryFn: () => activitiesApi.track(id),
    enabled: Boolean(id),
  })

  if (activity.isLoading || track.isLoading) return <ContentLoading label="Detailanalyse wird vorbereitet …" />
  if (activity.isError || !activity.data) {
    return <ErrorState error={activity.error ?? new Error('Aktivität nicht gefunden.')} onRetry={() => void activity.refetch()} />
  }
  if (track.isError || !track.data) {
    return <ErrorState error={track.error ?? new Error('Streckendaten konnten nicht geladen werden.')} onRetry={() => void track.refetch()} />
  }

  const item = activity.data

  return (
    <>
      <Button
        component={RouterLink}
        to={`/aktivitaeten/${id}`}
        color="inherit"
        startIcon={<ArrowBackRoundedIcon />}
        sx={{ mb: 2 }}
      >Zur Aktivität</Button>

      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'flex-end' }} gap={2.5} sx={{ mb: 3 }}>
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" alignItems="center" gap={1} flexWrap="wrap" sx={{ mb: .75 }}>
            <Chip color="primary" size="small" icon={<InsightsRoundedIcon />} label="Detaillierte Analyse" />
            <Chip size="small" variant="outlined" label={activityTypeLabels[item.type] ?? item.type} />
            <Typography variant="body2" color="text.secondary">{formatDateTime(item.started_at)}</Typography>
          </Stack>
          <Typography variant="h2" component="h1">{item.title}</Typography>
          <Typography color="text.secondary" sx={{ mt: .5 }}>
            Karte, Messwerte und frei wählbare Streckenabschnitte in einer synchronisierten Ansicht.
          </Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap">
          <Chip label={formatDistance(item.distance_m)} />
          <Chip label={formatDuration(item.moving_time_s)} />
          <Chip label={formatElevation(item.elevation_gain_m)} />
        </Stack>
      </Stack>

      <AdvancedActivityAnalysis points={track.data.points} weather={item.weather} />
    </>
  )
}
