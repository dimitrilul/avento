import AddRoundedIcon from '@mui/icons-material/AddRounded'
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded'
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import DirectionsBikeRoundedIcon from '@mui/icons-material/DirectionsBikeRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import { Box, Button, Card, CardContent, Skeleton, Stack, Typography, useTheme } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink, useOutletContext } from 'react-router-dom'
import { activitiesApi, statisticsApi } from '../api'
import { useAuth } from '../auth/AuthContext'
import { ActivityCard } from '../components/ActivityCard'
import { EmptyState, ErrorState } from '../components/States'
import { MetricCard } from '../components/MetricCard'
import { PageHeader } from '../components/PageHeader'
import { TrendChart } from '../components/TrendChart'
import type { ShellOutletContext } from '../layout/AppShell'
import { formatDistance, formatDuration, formatElevation } from '../utils/format'

export function DashboardPage() {
  const { profile } = useAuth()
  const { openImport } = useOutletContext<ShellOutletContext>()
  const theme = useTheme()
  const year = new Date().getFullYear()
  const dateFrom = `${year}-01-01`
  const dateTo = `${year}-12-31`
  const stats = useQuery({
    queryKey: ['statistics', 'overview', dateFrom, dateTo],
    queryFn: () => statisticsApi.overview(dateFrom, dateTo),
  })
  const recent = useQuery({
    queryKey: ['activities', { limit: 4 }],
    queryFn: () => activitiesApi.list({ limit: 4 }),
  })

  return (
    <>
      <PageHeader
        eyebrow="DEIN COCKPIT"
        title={`Hallo ${profile?.display_name?.split(' ')[0] ?? ''}`}
        description="Dein Radjahr auf einen Blick – aktuell, verständlich und bereit für die nächste Runde."
        action={<Button variant="contained" startIcon={<AddRoundedIcon />} onClick={openImport}>TCX importieren</Button>}
      />

      {stats.isError ? <ErrorState error={stats.error} onRetry={() => void stats.refetch()} /> : (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: { xs: 1.5, md: 2 }, mb: 3 }}>
          {stats.isLoading ? Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} variant="rounded" height={145} />) : (
            <>
              <MetricCard label={`Fahrten ${year}`} value={String(stats.data?.activity_count ?? 0)} icon={<DirectionsBikeRoundedIcon />} accent={theme.palette.chart.teal} hint="importierte Aktivitäten" />
              <MetricCard label="Distanz" value={formatDistance(stats.data?.distance_m)} icon={<RouteRoundedIcon />} accent={theme.palette.chart.blue} hint="im aktuellen Jahr" />
              <MetricCard label="Fahrzeit" value={formatDuration(stats.data?.moving_time_s)} icon={<AccessTimeRoundedIcon />} accent={theme.palette.chart.amber} hint="aktive Zeit" />
              <MetricCard label="Höhenmeter" value={formatElevation(stats.data?.elevation_gain_m)} icon={<LandscapeRoundedIcon />} accent={theme.palette.chart.coral} hint="positiver Anstieg" />
            </>
          )}
        </Box>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 1.45fr) minmax(360px, .75fr)' }, gap: 3, alignItems: 'start' }}>
        <Card>
          <CardContent sx={{ p: { xs: 2, sm: 3 }, '&:last-child': { pb: { xs: 2, sm: 3 } } }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Box>
                <Typography variant="h3">Distanz im Verlauf</Typography>
                <Typography variant="body2" color="text.secondary">Monatliche Kilometer · {year}</Typography>
              </Box>
              <Button component={RouterLink} to="/statistiken" endIcon={<ArrowForwardRoundedIcon />}>Details</Button>
            </Stack>
            {stats.isLoading ? <Skeleton variant="rounded" height={290} /> : stats.data?.by_month?.length ? <TrendChart data={stats.data.by_month} /> : (
              <EmptyState title="Noch kein Verlauf" description="Mit deiner ersten importierten Fahrt entsteht hier dein Jahresverlauf." action={<Button onClick={openImport}>Erste Fahrt importieren</Button>} />
            )}
          </CardContent>
        </Card>

        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="h3">Letzte Fahrten</Typography>
              <Typography variant="body2" color="text.secondary">Zuletzt importiert</Typography>
            </Box>
            <Button component={RouterLink} to="/aktivitaeten" endIcon={<ArrowForwardRoundedIcon />}>Alle</Button>
          </Stack>
          {recent.isError && <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />}
          {recent.isLoading && Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} variant="rounded" height={150} />)}
          {recent.data?.items.map((activity) => <ActivityCard key={activity.id} activity={activity} />)}
          {recent.data && recent.data.items.length === 0 && (
            <Card><EmptyState title="Noch keine Fahrt" description="Importiere eine TCX-Datei und starte deine persönliche Analyse." action={<Button variant="contained" onClick={openImport}>Importieren</Button>} /></Card>
          )}
        </Stack>
      </Box>
    </>
  )
}
