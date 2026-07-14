import { useEffect, useRef, useState } from 'react'
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded'
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded'
import EditRoundedIcon from '@mui/icons-material/EditRounded'
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded'
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded'
import TimerRoundedIcon from '@mui/icons-material/TimerRounded'
import WaterDropRoundedIcon from '@mui/icons-material/WaterDropRounded'
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, FormControl, InputLabel, MenuItem, Select, Skeleton, Stack, TextField, Typography,
} from '@mui/material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { activitiesApi, type Activity, type ActivityUpdate, type PersonalRecordsResponse } from '../../../api'
import { ActivityPhotoGallery } from '../../../components/ActivityPhotoGallery'
import { AdvancedActivityAnalysis } from '../../../components/AdvancedActivityAnalysis'
import { AiSummaryCard } from '../../../components/AiSummaryCard'
import { OverlayExportDialog } from '../../../components/OverlayExportDialog'
import { ContentLoading, ErrorState } from '../../../components/States'
import { WeatherCard } from '../../../components/WeatherCard'
import { useActivityDetailViewModel } from '../../../features/activities/useActivityDetailViewModel'
import type { AchievementInfo } from '../../../share/types'
import {
  activityTypeLabels, activityTypes, errorMessage, formatDateTime, formatDistance,
  formatDuration, formatElevation, formatHeartRate, formatHydration, formatSpeedMps,
} from '../../../utils/format'

export function MinimalActivityDetailPage() {
  const vm = useActivityDetailViewModel()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const deleteCancelRef = useRef<HTMLButtonElement>(null)
  if (vm.activity.isLoading) return <ContentLoading label="Aktivität wird geladen …" />
  if (vm.activity.isError || !vm.activity.data) return <ErrorState error={vm.activity.error ?? new Error('Aktivität nicht gefunden.')} onRetry={() => void vm.activity.refetch()} />
  const item = vm.activity.data
  const points = vm.track.data?.points ?? []
  const achievement = achievementForActivity(item.id, vm.records.data)
  const metrics = [
    ['Distanz', formatDistance(item.distance_m), <RouteRoundedIcon key="icon" />],
    ['Bewegungszeit', formatDuration(item.moving_time_s), <TimerRoundedIcon key="icon" />],
    ['Höhenmeter', formatElevation(item.elevation_gain_m), <LandscapeRoundedIcon key="icon" />],
    ['Ø Geschwindigkeit', formatSpeedMps(item.avg_speed_mps), <SpeedRoundedIcon key="icon" />],
    ['Ø Herzfrequenz', formatHeartRate(item.avg_hr_bpm), <FavoriteRoundedIcon key="icon" />],
    ['Trinkmenge', formatHydration(item.hydration_ml), <WaterDropRoundedIcon key="icon" />],
  ] as const
  return (
    <Stack spacing={{ xs: 4, md: 6 }}>
      <Box component="header">
        <Button component={RouterLink} to="/aktivitaeten" color="inherit" startIcon={<ArrowBackRoundedIcon />} sx={{ mb: 2 }}>Alle Aktivitäten</Button>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'flex-end' }} gap={2.5}>
          <Box sx={{ minWidth: 0, maxWidth: 850 }}>
            <Stack direction="row" gap= {1} alignItems="center" flexWrap="wrap">
              <Chip color="primary" size="small" label={activityTypeLabels[item.type] ?? item.type} />
              <Typography variant="body2" color="text.secondary">{formatDateTime(item.started_at)}</Typography>
            </Stack>
            <Typography component="h1" variant="h1" sx={{ mt: 1.25, overflowWrap: 'anywhere' }}>{item.title}</Typography>
            {item.original_filename && <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>Importiert aus {item.original_filename}</Typography>}
          </Box>
          <Stack direction="row" gap={1} flexWrap="wrap">
            <Button variant="outlined" startIcon={<AutorenewRoundedIcon />} disabled={vm.reanalyze.isPending} onClick={() => vm.reanalyze.mutate()}>{vm.reanalyze.isPending ? 'Wird berechnet …' : 'Neu analysieren'}</Button>
            <Button variant="outlined" startIcon={<EditRoundedIcon />} onClick={() => setEditOpen(true)}>Bearbeiten</Button>
            <Button variant="contained" startIcon={<DownloadRoundedIcon />} onClick={() => setExportOpen(true)}>PNG-Overlay</Button>
            <Button color="error" startIcon={<DeleteOutlineRoundedIcon />} onClick={() => setDeleteOpen(true)}>Löschen</Button>
          </Stack>
        </Stack>
      </Box>

      {vm.reanalyze.isError && <Alert severity="error">{errorMessage(vm.reanalyze.error)}</Alert>}

      <Box component="section" aria-label="Wichtigste Kennzahlen" sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))', xl: 'repeat(6, minmax(0, 1fr))' }, gap: { xs: 2, md: 3 } }}>
        {metrics.map(([label, value, icon]) => <Box key={label} sx={{ minWidth: 0 }}><Stack direction="row" alignItems="center" gap={.75} color="text.secondary" sx={{ '& svg': { fontSize: 17 } }}><>{icon}</><Typography variant="caption">{label}</Typography></Stack><Typography variant="h3" sx={{ mt: .75, overflowWrap: 'anywhere' }}>{value}</Typography></Box>)}
      </Box>

      <Box component="section" aria-labelledby="route-title">
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1} sx={{ mb: 2 }}><Box><Typography id="route-title" component="h2" variant="h2">Strecke und Messwerte</Typography><Typography color="text.secondary" sx={{ mt: .5 }}>Karte, Sensorwerte und Streckenabschnitte folgen demselben Messpunkt.</Typography></Box><Button component={RouterLink} to={`/aktivitaeten/${vm.id}/analyse`} startIcon={<InsightsRoundedIcon />}>In eigener Ansicht öffnen</Button></Stack>
        {vm.track.isLoading ? <Skeleton variant="rounded" height={520} /> : vm.track.isError ? <ErrorState error={vm.track.error} onRetry={() => void vm.track.refetch()} /> : <AdvancedActivityAnalysis points={points} weather={item.weather} minimal />}
      </Box>

      {(item.training_load != null || item.avg_power_w != null || item.avg_cadence_rpm != null) && (
        <Box component="section" aria-labelledby="load-title">
          <Typography id="load-title" component="h2" variant="h2">Belastung verstehen</Typography>
          <Box sx={{ mt: 2.5, display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', md: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>
            {item.training_load != null && <SecondaryMetric label="Trainingsbelastung" value={Math.round(item.training_load).toLocaleString('de-DE')} description="Orientierungswert aus Dauer und Intensität" />}
            {item.avg_power_w != null && <SecondaryMetric label="Ø Leistung" value={`${Math.round(item.avg_power_w)} W`} description="Gemessene mittlere Leistung" />}
            {item.avg_cadence_rpm != null && <SecondaryMetric label="Ø Kadenz" value={`${Math.round(item.avg_cadence_rpm)} rpm`} description="Gemessene mittlere Trittfrequenz" />}
          </Box>
        </Box>
      )}

      {achievement && <Card component="section" sx={{ bgcolor: 'var(--avento-minimal-surface-raised)' }}><CardContent sx={{ p: { xs: 2.5, md: 4 } }}><Typography variant="overline" color="secondary.main">Persönlicher Rekord</Typography><Typography variant="h2" sx={{ mt: 1 }}>{achievement.label}</Typography><Typography sx={{ mt: 1.5, fontSize: 'clamp(2.2rem, 8vw, 4.5rem)', fontWeight: 680, letterSpacing: '-.055em' }}>{achievement.value}</Typography><Typography color="text.secondary">{achievement.detail}</Typography><Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 2 }}><Button component={RouterLink} to="/rekorde">Alle Rekorde</Button><Button component={RouterLink} to="/meilensteine">Meilensteine</Button></Stack></CardContent></Card>}

      {vm.activityBadges.length > 0 && <Box component="section" aria-labelledby="activity-milestones-title"><Typography id="activity-milestones-title" component="h2" variant="h2">Mit dieser Aktivität erreicht</Typography><Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>{vm.activityBadges.map((badge) => <Card key={badge.id} sx={{ bgcolor: 'var(--avento-minimal-surface-raised)' }}><CardContent><Stack direction="row" justifyContent="space-between" gap={1}><Typography variant="overline" color="secondary.main">{badge.tier}</Typography><Chip size="small" label={`+${badge.reward_xp.toLocaleString('de-DE')} XP`} /></Stack><Typography variant="h3" sx={{ mt: 1 }}>{badge.name}</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>{badge.description}</Typography></CardContent></Card>)}</Box><Button component={RouterLink} to="/meilensteine" sx={{ mt: 1.5 }}>Alle Meilensteine ansehen</Button></Box>}

      <Box component="section" aria-label="Auswertung und Wetter" sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}><AiSummaryCard activityId={vm.id} fallback={item.ai_summary} provider={item.ai_provider} dataBasis={item.ai_data_basis} /><WeatherCard activityId={vm.id} fallback={item.weather} /></Box>
      <ActivityPhotoGallery activityId={vm.id} trackPoints={points} mapVariant="minimal" />

      <Box component="section" aria-labelledby="notes-title" sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'repeat(2, minmax(0, 1fr))' }, gap: 2 }}>
        <Card sx={{ bgcolor: 'var(--avento-minimal-surface-subtle)' }}><CardContent sx={{ p: 2.5 }}><Typography id="notes-title" component="h2" variant="h3">Notizen</Typography><Typography color={item.notes ? 'text.primary' : 'text.secondary'} sx={{ mt: 1.5, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.notes || 'Noch keine Notizen zu dieser Aktivität.'}</Typography><Button startIcon={<EditRoundedIcon />} sx={{ mt: 1.5 }} onClick={() => setEditOpen(true)}>Notizen bearbeiten</Button></CardContent></Card>
        <HeartRateZones activity={item} />
      </Box>

      <Button component={RouterLink} to={`/aktivitaeten/${vm.id}/analyse`} variant="contained" size="large" startIcon={<InsightsRoundedIcon />} sx={{ minHeight: 64 }}>Detaillierte Analyse öffnen</Button>

      <EditActivityDialog open={editOpen} onClose={() => setEditOpen(false)} activity={item} />
      <OverlayExportDialog open={exportOpen} onClose={() => setExportOpen(false)} activity={item} points={points} achievement={achievement} />
      <Dialog open={deleteOpen} onClose={vm.remove.isPending ? undefined : () => setDeleteOpen(false)} maxWidth="xs" fullWidth aria-describedby="delete-activity-description" slotProps={{ transition: { onEntered: () => deleteCancelRef.current?.focus() } }}>
        <DialogTitle>Aktivität löschen?</DialogTitle>
        <DialogContent><Typography id="delete-activity-description">„{item.title}“ und die zugehörige TCX-Datei werden dauerhaft gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.</Typography>{vm.remove.isError && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage(vm.remove.error)}</Alert>}</DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}><Button ref={deleteCancelRef} color="inherit" onClick={() => setDeleteOpen(false)}>Abbrechen</Button><Button color="error" variant="contained" disabled={vm.remove.isPending} onClick={() => vm.remove.mutate()}>{vm.remove.isPending ? 'Wird gelöscht …' : 'Endgültig löschen'}</Button></DialogActions>
      </Dialog>
    </Stack>
  )
}

function SecondaryMetric({ label, value, description }: { label: string; value: string; description: string }) {
  return <Card sx={{ bgcolor: 'var(--avento-minimal-surface-subtle)' }}><CardContent><Typography variant="body2" color="text.secondary">{label}</Typography><Typography variant="h2" sx={{ mt: .5 }}>{value}</Typography><Typography variant="caption" color="text.secondary">{description}</Typography></CardContent></Card>
}

function achievementForActivity(activityId: string, records?: PersonalRecordsResponse): AchievementInfo | null {
  if (!records) return null
  if (records.highest_elevation_gain?.activity_id === activityId) return { kind: 'elevation_record', label: 'Höhenmeter-Rekord', value: formatElevation(records.highest_elevation_gain.elevation_gain_m), detail: formatDistance(records.highest_elevation_gain.distance_m) }
  if (records.longest_ride?.activity_id === activityId) return { kind: 'longest_ride', label: 'Längste Tour', value: formatDistance(records.longest_ride.distance_m), detail: formatDuration(records.longest_ride.moving_time_s) }
  if (records.highest_average_speed?.activity_id === activityId) return { kind: 'fastest_ride', label: 'Schnellste Tour', value: formatSpeedMps(records.highest_average_speed.avg_speed_mps), detail: formatDistance(records.highest_average_speed.distance_m) }
  const record = records.distance_records.find((entry) => entry.activity_id === activityId)
  return record ? { kind: 'distance_pr', label: `Bestzeit über ${(record.target_distance_m / 1000).toLocaleString('de-DE')} km`, value: formatDuration(record.duration_s), detail: formatSpeedMps(record.avg_speed_mps), segmentStartM: record.segment_start_m, segmentEndM: record.segment_end_m } : null
}

function EditActivityDialog({ open, onClose, activity }: { open: boolean; onClose: () => void; activity: Activity }) {
  const client = useQueryClient()
  const titleInputRef = useRef<HTMLInputElement>(null)
  const [values, setValues] = useState<ActivityUpdate>({ title: activity.title, type: activity.type, notes: activity.notes, hydration_ml: activity.hydration_ml })
  useEffect(() => { if (open) setValues({ title: activity.title, type: activity.type, notes: activity.notes, hydration_ml: activity.hydration_ml }) }, [activity, open])
  const mutation = useMutation({ mutationFn: () => activitiesApi.update(activity.id, values), onSuccess: async (updated) => { client.setQueryData(['activity', activity.id], updated); await client.invalidateQueries({ queryKey: ['activities'] }); onClose() } })
  return <Dialog open={open} onClose={mutation.isPending ? undefined : onClose} fullWidth maxWidth="sm" aria-describedby="edit-activity-description" slotProps={{ transition: { onEntered: () => titleInputRef.current?.focus() } }}><DialogTitle>Aktivität bearbeiten</DialogTitle><DialogContent><Typography id="edit-activity-description" variant="body2" color="text.secondary" sx={{ mb: 2 }}>Titel, Sportart, Trinkmenge und private Notizen anpassen.</Typography><Stack spacing={2}>
    <TextField inputRef={titleInputRef} label="Titel" required fullWidth value={values.title ?? ''} onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))} />
    <FormControl fullWidth><InputLabel id="minimal-edit-type-label">Aktivitätstyp</InputLabel><Select labelId="minimal-edit-type-label" label="Aktivitätstyp" value={values.type ?? 'ride'} onChange={(event) => setValues((current) => ({ ...current, type: event.target.value }))}>{activityTypes.map((type) => <MenuItem key={type.value} value={type.value}>{type.label}</MenuItem>)}</Select></FormControl>
    <TextField label="Trinkmenge in Millilitern" type="number" value={values.hydration_ml ?? ''} onChange={(event) => setValues((current) => ({ ...current, hydration_ml: event.target.value === '' ? null : Number(event.target.value) }))} inputProps={{ min: 0, max: 20000, step: 50 }} />
    <TextField label="Private Notizen" multiline minRows={5} value={values.notes ?? ''} onChange={(event) => setValues((current) => ({ ...current, notes: event.target.value }))} />
    {mutation.isError && <Alert severity="error">{errorMessage(mutation.error)}</Alert>}
  </Stack></DialogContent><DialogActions sx={{ px: 3, pb: 3 }}><Button color="inherit" onClick={onClose}>Abbrechen</Button><Button variant="contained" disabled={mutation.isPending || !values.title?.trim() || (values.hydration_ml != null && (values.hydration_ml < 0 || values.hydration_ml > 20000))} onClick={() => mutation.mutate()}>{mutation.isPending ? 'Wird gespeichert …' : 'Speichern'}</Button></DialogActions></Dialog>
}

function HeartRateZones({ activity }: { activity: Activity }) {
  const zones = Object.entries(activity.hr_zone_seconds ?? {})
  const total = zones.reduce((sum, [, seconds]) => sum + seconds, 0)
  return <Card sx={{ bgcolor: 'var(--avento-minimal-surface-subtle)' }}><CardContent sx={{ p: 2.5 }}><Typography component="h2" variant="h3">Herzfrequenzzonen</Typography><Typography variant="body2" color="text.secondary">Zeit in den Trainingsbereichen</Typography>{zones.length ? <Stack spacing={1.25} sx={{ mt: 2 }}>{zones.map(([zone, seconds], index) => <Box key={zone}><Stack direction="row" justifyContent="space-between"><Typography variant="body2">{zone}</Typography><Typography variant="body2" color="text.secondary">{formatDuration(seconds)}</Typography></Stack><Box sx={{ mt: .5, height: 6, borderRadius: 4, bgcolor: 'action.hover', overflow: 'hidden' }}><Box sx={{ width: `${total ? seconds / total * 100 : 0}%`, height: '100%', bgcolor: ['chart.blue', 'chart.teal', 'chart.lime', 'chart.amber', 'chart.coral'][index % 5] }} /></Box></Box>)}</Stack> : <Typography color="text.secondary" sx={{ mt: 2 }}>Keine Herzfrequenzzonen verfügbar.</Typography>}</CardContent></Card>
}
