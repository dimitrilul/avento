import { useMemo } from 'react'
import BatteryChargingFullRoundedIcon from '@mui/icons-material/BatteryChargingFullRounded'
import BedtimeRoundedIcon from '@mui/icons-material/BedtimeRounded'
import DirectionsRunRoundedIcon from '@mui/icons-material/DirectionsRunRounded'
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded'
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded'
import MonitorHeartRoundedIcon from '@mui/icons-material/MonitorHeartRounded'
import OpenInNewRoundedIcon from '@mui/icons-material/OpenInNewRounded'
import SyncRoundedIcon from '@mui/icons-material/SyncRounded'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  useTheme,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link as RouterLink } from 'react-router-dom'
import {
  healthApi,
  healthQueryKeys,
  type HealthConnectionStatus,
  type HealthDataResponse,
  type HealthMetric,
  type HealthOverviewResponse,
  type HealthScore,
  type HealthScoreFactor,
  type HealthSleep,
} from '../api'
import { ContentLoading, EmptyState, ErrorState } from '../components/States'
import { PageHeader } from '../components/PageHeader'
import { formatDate, formatDateTime, formatDistance, formatDuration } from '../utils/format'

function localDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function healthScore(overview: HealthOverviewResponse | undefined, key: string): HealthScore | null {
  const value = overview?.scores?.[key]
  return isRecord(value) ? value as HealthScore : null
}

function scoreNumber(score: HealthScore | null) {
  if (typeof score?.value === 'number') return score.value
  if (typeof score?.score === 'number') return score.score
  return null
}

function statusText(status?: string) {
  const labels: Record<string, string> = {
    available: 'Verfügbar',
    missing_required_data: 'Zentrale Daten fehlen',
    insufficient_baseline: 'Vergleichsbasis noch zu kurz',
    insufficient_coverage: 'Datenabdeckung zu gering',
    incomplete_data: 'Tag noch unvollständig',
  }
  return labels[status ?? ''] ?? 'Noch kein Score'
}

function scoreLevel(level?: string | null) {
  return level?.replaceAll('_', ' ') ?? null
}

function formatMetric(metric?: HealthMetric, maximumFractionDigits = 0) {
  if (!metric) return '–'
  const unit = metric.unit === 'count' ? 'Schritte' : metric.unit
  return `${metric.value.toLocaleString('de-DE', { maximumFractionDigits })} ${unit}`
}

function latestMetric(data: HealthDataResponse | undefined, types: string[], day?: string) {
  return data?.metrics.find((metric) => types.includes(metric.metric_type) && (!day || metric.local_date === day))
    ?? data?.metrics.find((metric) => types.includes(metric.metric_type))
}

function hasHealthData(data?: HealthDataResponse) {
  return Boolean(data && (data.metrics.length || data.heart_rate.length || data.sleeps.length || data.exercises.length))
}

function mainSleep(data?: HealthDataResponse) {
  return data?.sleeps.find((sleep) => !sleep.is_nap) ?? data?.sleeps[0]
}

export function HealthPage() {
  const queryClient = useQueryClient()
  const today = localDate(new Date())
  const from = new Date()
  from.setDate(from.getDate() - 29)
  const filters = { dateFrom: localDate(from), dateTo: today, limit: 1000 }
  const connection = useQuery({ queryKey: healthQueryKeys.connection, queryFn: healthApi.connection })
  const enabled = connection.data?.connected === true
  const overview = useQuery({
    queryKey: healthQueryKeys.overview(today),
    queryFn: () => healthApi.overview(today),
    enabled,
  })
  const data = useQuery({
    queryKey: healthQueryKeys.data(filters),
    queryFn: () => healthApi.data(filters),
    enabled,
  })
  const sync = useMutation({
    mutationFn: () => healthApi.sync(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: healthQueryKeys.all })
    },
  })

  if (connection.isLoading) return <ContentLoading label="Google Health wird geladen …" />
  if (connection.isError) return <ErrorState error={connection.error} onRetry={() => void connection.refetch()} />

  const syncButton = connection.data?.connected ? (
    <Button
      variant="contained"
      startIcon={<SyncRoundedIcon />}
      disabled={sync.isPending}
      onClick={() => sync.mutate()}
    >
      {sync.isPending ? 'Synchronisiert …' : 'Synchronisieren'}
    </Button>
  ) : undefined

  return (
    <>
      <PageHeader
        eyebrow="GOOGLE HEALTH"
        title="Gesundheitsübersicht"
        description="Tagesform, Schlaf, Bewegung und Belastung auf Basis deiner synchronisierten Google-Health-Daten."
        action={syncButton}
      />

      {!connection.data?.connected ? (
        <DisconnectedState connection={connection.data} />
      ) : (overview.isLoading || data.isLoading) && !overview.data && !data.data ? (
        <ContentLoading label="Gesundheitsdaten und serverseitige Scores werden geladen …" />
      ) : overview.isError && data.isError ? (
        <ErrorState
          error={overview.error}
          onRetry={() => { void overview.refetch(); void data.refetch() }}
        />
      ) : !hasHealthData(data.data) && !hasAnyServerScore(overview.data) ? (
        <EmptyState
          title="Noch keine Gesundheitsdaten"
          description="Die Verbindung steht, aber Avento hat noch keine Daten erhalten. Starte eine Synchronisation und prüfe anschließend diese Übersicht erneut."
          action={syncButton}
        />
      ) : (
        <Stack spacing={2.5}>
          {(overview.isError || data.isError) && (
            <Alert severity="warning">
              Ein Teil der Gesundheitsansicht ist gerade nicht verfügbar. Vorhandene Daten werden weiterhin angezeigt.
            </Alert>
          )}
          {sync.isError && <Alert severity="error">Die Synchronisation ist fehlgeschlagen. Bitte versuche es erneut.</Alert>}
          {sync.data && (
            <Alert severity={sync.data.status === 'succeeded' ? 'success' : 'warning'}>
              Synchronisation abgeschlossen: {sync.data.stored_count} Datensätze übernommen,
              {' '}{sync.data.rejected_count} verworfen.
            </Alert>
          )}
          <Alert severity="info" icon={<MonitorHeartRoundedIcon />}>
            Die Scores werden ausschließlich serverseitig und deterministisch berechnet – nicht durch KI.
            Sie dienen der Fitness- und Wellness-Einordnung, sind keine medizinische Diagnose und ersetzen
            keine ärztliche Beratung.
          </Alert>

          <DailyScores overview={overview.data} />
          <SleepAndMovement data={data.data} overview={overview.data} />
          <TrainingSection data={data.data} score={healthScore(overview.data, 'training_load')} />
          <TrendSection data={data.data} />
          <SourcesSection connection={connection.data} data={data.data} generatedAt={overview.data?.generated_at} />
        </Stack>
      )}
    </>
  )
}

function DisconnectedState({ connection }: { connection?: HealthConnectionStatus }) {
  const disabled = connection?.enabled === false
  return (
    <Card>
      <CardContent sx={{ p: { xs: 3, md: 4 } }}>
        <EmptyState
          title={disabled ? 'Google Health ist auf diesem Server deaktiviert' : 'Google Health ist nicht verbunden'}
          description={disabled
            ? 'Aktiviere zuerst die Google-Health-Konfiguration im Avento-Backend oder nutze den sicheren lokalen Mockmodus.'
            : connection?.status === 'reauthorization_required'
            ? 'Die bisherige Freigabe muss erneuert werden. Öffne dein Profil, um Google Health erneut zu autorisieren.'
            : 'Verbinde Google Health im Profil, um Schlaf-, Fitness- und ausgewählte Messdaten in Avento zu sehen.'}
          action={disabled ? undefined : <Button component={RouterLink} to="/profil" variant="contained" endIcon={<OpenInNewRoundedIcon />}>Google Health verbinden</Button>}
        />
      </CardContent>
    </Card>
  )
}

function hasAnyServerScore(overview?: HealthOverviewResponse) {
  return ['recovery', 'energy', 'training_load', 'resilience'].some((key) => scoreNumber(healthScore(overview, key)) !== null)
}

function DailyScores({ overview }: { overview?: HealthOverviewResponse }) {
  const items = [
    { key: 'recovery', label: 'Tagesform / Recovery', icon: <FavoriteRoundedIcon /> },
    { key: 'energy', label: 'Energie', icon: <BatteryChargingFullRoundedIcon /> },
    { key: 'training_load', label: 'Trainingsbelastung', icon: <DirectionsRunRoundedIcon /> },
    { key: 'resilience', label: 'Langfristige Resilienz', icon: <InsightsRoundedIcon /> },
  ]
  return (
    <Card component="section" aria-labelledby="daily-form-title">
      <CardContent sx={{ p: 0 }}>
        <Box sx={{ p: { xs: 2.5, md: 3 }, pb: 2 }}>
          <Typography id="daily-form-title" variant="h3">Tagesform und Energie</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Persönliche Einordnung für {formatDate(overview?.date)}; Werte ohne ausreichende Basis bleiben bewusst leer.
          </Typography>
        </Box>
        <Divider />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', xl: 'repeat(4, 1fr)' } }}>
          {items.map((item, index) => (
            <ScoreTile
              key={item.key}
              label={item.label}
              icon={item.icon}
              score={healthScore(overview, item.key)}
              divider={index < items.length - 1}
            />
          ))}
        </Box>
        {(overview?.uncertainty.length ?? 0) > 0 && (
          <Box sx={{ px: { xs: 2.5, md: 3 }, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
            {overview?.uncertainty.map((message) => (
              <Typography key={message} variant="body2" color="warning.main">{message}</Typography>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

function ScoreTile({
  label,
  icon,
  score,
  divider,
}: {
  label: string
  icon: React.ReactNode
  score: HealthScore | null
  divider: boolean
}) {
  const value = scoreNumber(score)
  const factors = score?.important_factors ?? score?.factors?.filter((factor) => factor.status === 'available').slice(0, 2) ?? []
  const coverage = score?.data_coverage?.percent
  return (
    <Box sx={{ p: { xs: 2.5, md: 3 }, borderRight: { xl: divider ? '1px solid' : 0 }, borderBottom: { xs: divider ? '1px solid' : 0, xl: 0 }, borderColor: 'divider', minWidth: 0 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
        <Typography variant="overline" color="text.secondary" fontWeight={800}>{label}</Typography>
        <Box sx={{ color: 'primary.main', display: 'grid', placeItems: 'center' }}>{icon}</Box>
      </Stack>
      {value === null ? (
        <>
          <Typography variant="h3" sx={{ mt: 1.5 }}>Kein Score</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>{statusText(score?.status)}</Typography>
        </>
      ) : (
        <>
          <Stack direction="row" alignItems="baseline" gap={0.75} sx={{ mt: 1 }}>
            <Typography sx={{ fontSize: '2.25rem', lineHeight: 1, fontWeight: 780 }}>{value.toLocaleString('de-DE')}</Typography>
            <Typography color="text.secondary">/ 100</Typography>
          </Stack>
          <Typography variant="body2" sx={{ mt: 1, textTransform: 'capitalize' }}>
            {scoreLevel(score?.level) ?? statusText(score?.status)}
            {score?.confidence ? ` · Sicherheit ${score.confidence}` : ''}
          </Typography>
          {typeof coverage === 'number' && (
            <Box sx={{ mt: 1.5 }}>
              <Stack direction="row" justifyContent="space-between" mb={0.5}>
                <Typography variant="caption" color="text.secondary">Datenabdeckung</Typography>
                <Typography variant="caption">{coverage.toLocaleString('de-DE', { maximumFractionDigits: 0 })} %</Typography>
              </Stack>
              <LinearProgress variant="determinate" value={Math.min(100, Math.max(0, coverage))} sx={{ height: 5, borderRadius: '8px' }} />
            </Box>
          )}
        </>
      )}
      {factors.length > 0 && (
        <Stack spacing={0.5} sx={{ mt: 1.5 }}>
          {factors.map((factor, index) => <FactorLine key={`${factor.key ?? factor.label}-${index}`} factor={factor} />)}
        </Stack>
      )}
    </Box>
  )
}

function FactorLine({ factor }: { factor: HealthScoreFactor }) {
  const prefix = factor.impact === 'positiv' ? '↑' : factor.impact === 'negativ' ? '↓' : '•'
  return (
    <Typography variant="caption" color="text.secondary" noWrap title={factor.reason ?? factor.label}>
      {prefix} {factor.label ?? factor.key ?? 'Einflussfaktor'}
    </Typography>
  )
}

function SleepAndMovement({ data, overview }: { data?: HealthDataResponse; overview?: HealthOverviewResponse }) {
  const sleep = mainSleep(data)
  const day = overview?.date
  const steps = latestMetric(data, ['steps'], day)
  const activeCalories = latestMetric(data, ['active_calories'], day)
  const totalCalories = latestMetric(data, ['total_calories'], day)
  const restingHeartRate = latestMetric(data, ['resting_heart_rate'], day)
  return (
    <Card component="section" aria-label="Schlaf und Bewegung">
      <CardContent sx={{ p: 0 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' } }}>
          <Box sx={{ p: { xs: 2.5, md: 3 }, borderRight: { lg: '1px solid' }, borderBottom: { xs: '1px solid', lg: 0 }, borderColor: 'divider' }}>
            <Stack direction="row" alignItems="center" gap={1} mb={2}>
              <BedtimeRoundedIcon color="primary" />
              <Typography variant="h3">Schlaf</Typography>
            </Stack>
            {sleep ? <SleepSummary sleep={sleep} /> : <Typography color="text.secondary">Für diesen Zeitraum liegt noch kein Schlaf vor.</Typography>}
          </Box>
          <Box sx={{ p: { xs: 2.5, md: 3 } }}>
            <Stack direction="row" alignItems="center" gap={1} mb={2}>
              <DirectionsRunRoundedIcon color="primary" />
              <Typography variant="h3">Bewegung</Typography>
            </Stack>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2.5 }}>
              <RawMetric label="Schritte" value={formatMetric(steps)} />
              <RawMetric label="Aktive Energie" value={formatMetric(activeCalories, 1)} />
              <RawMetric label="Gesamtenergie" value={formatMetric(totalCalories, 1)} />
              <RawMetric label="Ruhepuls" value={formatMetric(restingHeartRate)} />
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  )
}

function SleepSummary({ sleep }: { sleep: HealthSleep }) {
  const stageNames: Record<string, string> = { AWAKE: 'Wach', LIGHT: 'Leicht', DEEP: 'Tief', REM: 'REM', ASLEEP: 'Schlaf', RESTLESS: 'Unruhig' }
  const presentStages = [...new Set(sleep.stages.map((stage) => stageNames[stage.stage_type] ?? stage.stage_type))]
  return (
    <Stack spacing={1.25}>
      <Stack direction="row" alignItems="baseline" gap={1}>
        <Typography sx={{ fontSize: '2rem', fontWeight: 760 }}>{formatDuration((sleep.minutes_asleep ?? 0) * 60)}</Typography>
        <Typography variant="body2" color="text.secondary">geschlafen</Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        {formatDateTime(sleep.start_at)} – {formatDateTime(sleep.end_at)}
      </Typography>
      {sleep.minutes_awake != null && <Typography variant="body2">Wachzeit: {sleep.minutes_awake} Min.</Typography>}
      {presentStages.length > 0 && <Typography variant="body2">Phasen: {presentStages.join(' · ')}</Typography>}
      {sleep.overlaps_other_session && <Alert severity="warning">Diese Schlafsitzung überschneidet sich mit einer weiteren Aufzeichnung.</Alert>}
    </Stack>
  )
}

function RawMetric({ label, value }: { label: string; value: string }) {
  return <Box><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="h4" sx={{ mt: 0.25 }}>{value}</Typography></Box>
}

function TrainingSection({ data, score }: { data?: HealthDataResponse; score: HealthScore | null }) {
  const exercises = data?.exercises.slice(0, 4) ?? []
  return (
    <Card component="section" aria-labelledby="training-load-title">
      <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" gap={2}>
          <Box>
            <Typography id="training-load-title" variant="h3">Trainingsbelastung</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Herzfrequenzzonen und Aktivitätsdaten werden serverseitig in die persönliche Einordnung überführt.
            </Typography>
          </Box>
          {typeof score?.raw_value === 'number' && (
            <Box sx={{ minWidth: 180 }}><RawMetric label="Heutige Belastung" value={`${score.raw_value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} ${score.raw_unit ?? 'Punkte'}`} /></Box>
          )}
        </Stack>
        <Divider sx={{ my: 2.5 }} />
        {exercises.length ? (
          <Stack divider={<Divider flexItem />}>
            {exercises.map((exercise) => (
              <Stack key={exercise.id} direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1} py={1.5}>
                <Box><Typography fontWeight={700}>{exercise.title || exercise.exercise_type.replaceAll('_', ' ')}</Typography><Typography variant="caption" color="text.secondary">{formatDateTime(exercise.start_at)}</Typography></Box>
                <Stack direction="row" gap={2} flexWrap="wrap">
                  <Typography variant="body2">{formatDuration(exercise.active_duration_seconds)}</Typography>
                  {exercise.distance_m != null && <Typography variant="body2">{formatDistance(exercise.distance_m)}</Typography>}
                  {exercise.active_zone_minutes != null && <Typography variant="body2">{exercise.active_zone_minutes} Zonenmin.</Typography>}
                  {exercise.average_heart_rate_bpm != null && <Typography variant="body2">Ø {exercise.average_heart_rate_bpm} bpm</Typography>}
                </Stack>
              </Stack>
            ))}
          </Stack>
        ) : <Typography color="text.secondary">Keine Trainingseinheiten im gewählten Zeitraum.</Typography>}
      </CardContent>
    </Card>
  )
}

interface TrendRow {
  date: string
  steps?: HealthMetric
  hrv?: HealthMetric
  resting?: HealthMetric
}

function TrendSection({ data }: { data?: HealthDataResponse }) {
  const theme = useTheme()
  const rows = useMemo(() => {
    const byDate = new Map<string, TrendRow>()
    for (const metric of data?.metrics ?? []) {
      if (!metric.local_date) continue
      const row = byDate.get(metric.local_date) ?? { date: metric.local_date }
      if (metric.metric_type === 'steps' && !row.steps) row.steps = metric
      if (metric.metric_type === 'hrv_rmssd' && !row.hrv) row.hrv = metric
      if (metric.metric_type === 'resting_heart_rate' && !row.resting) row.resting = metric
      byDate.set(metric.local_date, row)
    }
    return [...byDate.values()].sort((left, right) => right.date.localeCompare(left.date)).slice(0, 8)
  }, [data])
  const stepTrend = [...rows]
    .reverse()
    .filter((row): row is TrendRow & { steps: HealthMetric } => Boolean(row.steps))
    .map((row) => ({ date: row.date, label: formatDate(row.date), steps: row.steps.value }))
  return (
    <Card component="section" aria-labelledby="health-trends-title">
      <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
        <Typography id="health-trends-title" variant="h3">Langfristige Trends</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
          Rohwerte der letzten Tage; daraus wird im Browser kein Score berechnet.
        </Typography>
        {rows.length ? (<>
          {stepTrend.length >= 8 && (
            <Box sx={{ height: 220, mb: 2.5 }} role="img" aria-label="Schritte der letzten acht erfassten Tage">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stepTrend} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                  <CartesianGrid stroke={theme.palette.divider} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} axisLine={{ stroke: theme.palette.divider }} />
                  <YAxis width={48} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} domain={[0, 'auto']} />
                  <Tooltip
                    formatter={(value) => [`${Number(value).toLocaleString('de-DE')} Schritte`, 'Schritte']}
                    contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }}
                  />
                  <Line type="monotone" dataKey="steps" stroke={theme.palette.chart.teal} strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          )}
          <TableContainer>
            <Table size="small" aria-label="Gesundheitstrends">
              <TableHead><TableRow><TableCell>Tag</TableCell><TableCell align="right">Schritte</TableCell><TableCell align="right">HRV</TableCell><TableCell align="right">Ruhepuls</TableCell></TableRow></TableHead>
              <TableBody>{rows.map((row) => <TableRow key={row.date}><TableCell>{formatDate(row.date)}</TableCell><TableCell align="right">{formatMetric(row.steps)}</TableCell><TableCell align="right">{formatMetric(row.hrv, 1)}</TableCell><TableCell align="right">{formatMetric(row.resting)}</TableCell></TableRow>)}</TableBody>
            </Table>
          </TableContainer>
        </>) : <Typography color="text.secondary">Noch nicht genügend Tageswerte für einen Verlauf.</Typography>}
      </CardContent>
    </Card>
  )
}

function SourcesSection({ connection, data, generatedAt }: { connection: HealthConnectionStatus; data?: HealthDataResponse; generatedAt?: string }) {
  const sources = connection.data_sources ?? []
  return (
    <Box component="section" aria-labelledby="health-sources-title" sx={{ border: '1px solid', borderColor: 'divider', borderRadius: '12px', p: { xs: 2.5, md: 3 }, bgcolor: 'background.paper' }}>
      <Typography id="health-sources-title" variant="h3">Datenquelle und Synchronisationsstatus</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 2.5, mt: 2 }}>
        <RawMetric label="Quelle" value="Google Health API" />
        <RawMetric label="Letzte Synchronisation" value={formatDateTime(connection.last_sync_at)} />
        <RawMetric label="Ansicht erzeugt" value={formatDateTime(generatedAt ?? null)} />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
        Google gleicht Messwerte von Fitbit, Pixel Watch und unterstützten Drittanbieterquellen ab.
        Avento zeigt {data ? `${data.metrics.length} Messwerte, ${data.sleeps.length} Schlafsitzungen und ${data.exercises.length} Trainings` : 'die verfügbaren Datensätze'} aus dem gewählten Zeitraum.
      </Typography>
      {sources.length > 0 && (
        <Stack divider={<Divider flexItem />} sx={{ mt: 2 }}>
          {sources.map((source, index) => (
            <Stack key={`${source.platform}-${source.device_name}-${source.application_name}-${index}`} direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={0.5} py={1}>
              <Typography variant="body2" fontWeight={700}>
                {[source.device_manufacturer, source.device_name].filter(Boolean).join(' ') || source.application_name || 'Google-Health-Quelle'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {[source.platform, source.application_name, source.last_seen_at ? `zuletzt ${formatDateTime(source.last_seen_at)}` : null].filter(Boolean).join(' · ')}
              </Typography>
            </Stack>
          ))}
        </Stack>
      )}
      {connection.last_error_code && <Alert severity="warning" sx={{ mt: 2 }}>Letzter Synchronisationsfehler: {connection.last_error_code}</Alert>}
    </Box>
  )
}
