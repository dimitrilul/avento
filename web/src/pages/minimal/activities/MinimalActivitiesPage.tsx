import AddRoundedIcon from '@mui/icons-material/AddRounded'
import ClearAllRoundedIcon from '@mui/icons-material/ClearAllRounded'
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SearchRoundedIcon from '@mui/icons-material/SearchRounded'
import TimerRoundedIcon from '@mui/icons-material/TimerRounded'
import {
  Box, Button, Card, CardActionArea, Chip, InputAdornment, MenuItem, Pagination,
  Skeleton, Stack, TextField, Typography,
} from '@mui/material'
import { Link as RouterLink, useOutletContext } from 'react-router-dom'
import type { Activity } from '../../../api'
import { EmptyState, ErrorState } from '../../../components/States'
import { ActivityRoutePreview } from '../../../features/activities/ActivityRoutePreview'
import { activitiesPageSize, useActivitiesViewModel } from '../../../features/activities/useActivitiesViewModel'
import type { ShellOutletContext } from '../../../layout/AppShell'
import { activityTypeLabels, activityTypes, formatDateTime, formatDistance, formatDuration, formatElevation, formatHeartRate } from '../../../utils/format'

export function MinimalActivitiesPage() {
  const { openImport } = useOutletContext<ShellOutletContext>()
  const vm = useActivitiesViewModel()
  const total = vm.query.data?.total
  return (
    <Stack spacing={{ xs: 4, md: 6 }}>
      <Stack component="header" direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'flex-end' }} gap={2.5}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="overline" color="primary.main">Trainingstagebuch</Typography>
          <Typography component="h1" variant="h1" sx={{ mt: 1 }}>Aktivitäten</Typography>
          <Typography color="text.secondary" sx={{ mt: 1.5 }}>{total == null ? 'Deine Fahrten chronologisch im Blick.' : `${total.toLocaleString('de-DE')} ${total === 1 ? 'Aktivität' : 'Aktivitäten'}, klar nach Wochen geordnet.`}</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={openImport}>Importieren</Button>
      </Stack>

      <Card component="section" aria-label="Aktivitäten filtern" sx={{ bgcolor: 'var(--avento-minimal-surface-subtle)' }}>
        <Box sx={{ p: { xs: 2, md: 2.5 }, display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'minmax(220px, 1fr) 170px', lg: 'minmax(260px, 1fr) 170px 160px 160px auto' }, gap: 1.25 }}>
          <TextField placeholder="Titel oder Dateiname" value={vm.search} onChange={(event) => vm.update('q', event.target.value)} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRoundedIcon /></InputAdornment> }, htmlInput: { 'aria-label': 'Aktivitäten suchen' } }} />
          <TextField select label="Sportart" value={vm.type} onChange={(event) => vm.update('type', event.target.value)}>
            <MenuItem value="">Alle Sportarten</MenuItem>
            {activityTypes.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
          </TextField>
          <TextField label="Von" type="date" value={vm.dateFrom} onChange={(event) => vm.update('date_from', event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          <TextField label="Bis" type="date" value={vm.dateTo} onChange={(event) => vm.update('date_to', event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
          {vm.hasFilters && <Button color="inherit" startIcon={<ClearAllRoundedIcon />} onClick={vm.reset}>Zurücksetzen</Button>}
        </Box>
      </Card>

      {vm.query.isError && <ErrorState error={vm.query.error} onRetry={() => void vm.query.refetch()} />}
      {vm.query.isLoading && <Stack spacing={2}>{Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} variant="rounded" height={146} />)}</Stack>}
      {vm.query.data && vm.query.data.items.length > 0 && (
        <Stack spacing={4}>
          {vm.groups.map((group) => (
            <Box component="section" aria-labelledby={`week-${group.key}`} key={group.key}>
              <Stack direction="row" alignItems="baseline" gap={1.5} sx={{ mb: 1.5 }}>
                <Typography id={`week-${group.key}`} component="h2" variant="h3">Woche ab {group.label.split(' – ')[0]}</Typography>
                <Typography variant="body2" color="text.secondary">{group.label}</Typography>
              </Stack>
              <Stack spacing={1.25}>{group.activities.map((activity) => <MinimalActivityRow key={activity.id} activity={activity} />)}</Stack>
            </Box>
          ))}
          {vm.query.data.total > activitiesPageSize && <Stack alignItems="center"><Pagination page={vm.page} count={Math.ceil(vm.query.data.total / activitiesPageSize)} color="primary" onChange={(_, page) => { vm.update('page', String(page)); window.scrollTo({ top: 0, behavior: 'smooth' }) }} /></Stack>}
        </Stack>
      )}
      {vm.query.data && vm.query.data.items.length === 0 && <EmptyState title={vm.hasFilters ? 'Keine Treffer' : 'Noch keine Aktivitäten'} description={vm.hasFilters ? 'Passe Suche, Sportart oder Zeitraum an.' : 'Importiere deine erste TCX-Datei und beginne dein Trainingstagebuch.'} action={vm.hasFilters ? <Button onClick={vm.reset}>Filter zurücksetzen</Button> : <Button variant="contained" onClick={openImport}>Erste Aktivität importieren</Button>} />}
    </Stack>
  )
}

function MinimalActivityRow({ activity }: { activity: Activity }) {
  const values = [
    [<RouteRoundedIcon key="icon" />, formatDistance(activity.distance_m)],
    [<TimerRoundedIcon key="icon" />, formatDuration(activity.moving_time_s)],
    [<LandscapeRoundedIcon key="icon" />, formatElevation(activity.elevation_gain_m)],
    [<FavoriteRoundedIcon key="icon" />, formatHeartRate(activity.avg_hr_bpm)],
  ] as const
  return (
    <Card sx={{ overflow: 'hidden', bgcolor: 'var(--avento-minimal-surface-raised)' }}>
      <CardActionArea component={RouterLink} to={`/aktivitaeten/${activity.id}`} sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', sm: 'minmax(0, 1fr) 190px' }, alignItems: 'stretch' }}>
        <Box sx={{ p: { xs: 2.25, md: 2.75 }, minWidth: 0 }}>
          <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h4" sx={{ overflowWrap: 'anywhere' }}>{activity.title}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>{formatDateTime(activity.started_at)}</Typography>
            </Box>
            <Chip size="small" label={activityTypeLabels[activity.type] ?? activity.type} />
          </Stack>
          <Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', columnGap: 2, rowGap: 1 }}>
            {values.map(([icon, value], index) => <Stack key={index} direction="row" gap={.75} alignItems="center" minWidth={0} color="text.secondary" sx={{ '& svg': { fontSize: 17, flexShrink: 0 } }}><>{icon}</><Typography variant="body2" color="text.primary" noWrap>{value}</Typography></Stack>)}
          </Box>
        </Box>
        <Box sx={{ display: { xs: 'none', sm: 'block' }, alignSelf: 'center', px: 2, color: 'primary.main', borderLeft: '1px solid', borderColor: 'divider' }}><ActivityRoutePreview activityId={activity.id} /></Box>
      </CardActionArea>
    </Card>
  )
}
