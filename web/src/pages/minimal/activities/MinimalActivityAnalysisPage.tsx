import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded'
import { Box, Button, Chip, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { AdvancedActivityAnalysis } from '../../../components/AdvancedActivityAnalysis'
import { ContentLoading, ErrorState } from '../../../components/States'
import { useActivityDetailViewModel } from '../../../features/activities/useActivityDetailViewModel'
import { activityTypeLabels, formatDateTime, formatDistance, formatDuration, formatElevation } from '../../../utils/format'

export function MinimalActivityAnalysisPage() {
  const vm = useActivityDetailViewModel()
  if (vm.activity.isLoading || vm.track.isLoading) return <ContentLoading label="Detailanalyse wird vorbereitet …" />
  if (vm.activity.isError || !vm.activity.data) return <ErrorState error={vm.activity.error ?? new Error('Aktivität nicht gefunden.')} onRetry={() => void vm.activity.refetch()} />
  if (vm.track.isError || !vm.track.data) return <ErrorState error={vm.track.error ?? new Error('Streckendaten konnten nicht geladen werden.')} onRetry={() => void vm.track.refetch()} />
  const item = vm.activity.data
  return (
    <Stack spacing={{ xs: 4, md: 5 }}>
      <Box component="header">
        <Button component={RouterLink} to={`/aktivitaeten/${vm.id}`} color="inherit" startIcon={<ArrowBackRoundedIcon />} sx={{ mb: 2 }}>Zur Aktivität</Button>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'flex-end' }} gap={2.5}>
          <Box sx={{ minWidth: 0, maxWidth: 880 }}>
            <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap"><Chip color="primary" size="small" icon={<InsightsRoundedIcon />} label="Detaillierte Analyse" /><Chip size="small" variant="outlined" label={activityTypeLabels[item.type] ?? item.type} /><Typography variant="body2" color="text.secondary">{formatDateTime(item.started_at)}</Typography></Stack>
            <Typography component="h1" variant="h1" sx={{ mt: 1.25, overflowWrap: 'anywhere' }}>{item.title}</Typography>
            <Typography color="text.secondary" sx={{ mt: 1.5 }}>Karte, Sensorwerte und frei wählbare Streckenabschnitte folgen demselben Messpunkt.</Typography>
          </Box>
          <Stack direction="row" gap={1} flexWrap="wrap"><Chip label={formatDistance(item.distance_m)} /><Chip label={formatDuration(item.moving_time_s)} /><Chip label={formatElevation(item.elevation_gain_m)} /></Stack>
        </Stack>
      </Box>
      <AdvancedActivityAnalysis points={vm.track.data.points} weather={item.weather} minimal />
    </Stack>
  )
}
