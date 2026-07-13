import { forwardRef, useMemo, useRef, useState } from 'react'
import CheckRoundedIcon from '@mui/icons-material/CheckRounded'
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded'
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import TuneRoundedIcon from '@mui/icons-material/TuneRounded'
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from '@mui/material'
import { toPng } from 'html-to-image'
import type { Activity, TrackPoint } from '../api'
import {
  formatDate,
  formatDistance,
  formatDuration,
  formatElevation,
  formatHeartRate,
  formatHydration,
  formatSpeedMps,
} from '../utils/format'

type MetricKey = 'distance' | 'movingTime' | 'elevation' | 'avgSpeed' | 'heartRate' | 'maxSpeed' | 'power' | 'cadence' | 'duration' | 'hydration'

type OverlayPreset = {
  id: string
  name: string
  description: string
  background: string
  foreground: string
  muted: string
  accent: string
  transparent: boolean
  showRoute: boolean
  showPulse: boolean
  routePanel: boolean
  compact: boolean
  metrics: MetricKey[]
}

export const OVERLAY_PRESETS: OverlayPreset[] = [
  { id: 'avento', name: 'Avento', description: 'Karte · Puls', background: 'radial-gradient(circle at 85% 12%, rgba(165,200,56,.58), transparent 31%), linear-gradient(145deg, #072F2F 0%, #0E6562 72%, #397A53 100%)', foreground: '#fff', muted: 'rgba(255,255,255,.64)', accent: '#A5C838', transparent: false, showRoute: true, showPulse: true, routePanel: false, compact: false, metrics: ['distance', 'movingTime', 'elevation', 'heartRate'] },
  { id: 'midnight', name: 'Midnight', description: 'Karte · ohne Puls', background: 'linear-gradient(145deg, #080B18, #17234A 58%, #315CA8)', foreground: '#fff', muted: 'rgba(255,255,255,.6)', accent: '#6EC8FF', transparent: false, showRoute: true, showPulse: false, routePanel: true, compact: false, metrics: ['distance', 'movingTime', 'avgSpeed', 'elevation'] },
  { id: 'paper', name: 'Papier', description: 'Hell · ohne Karte', background: 'linear-gradient(135deg, #FFFDF7, #F0EBDD)', foreground: '#172927', muted: 'rgba(23,41,39,.58)', accent: '#D5694E', transparent: false, showRoute: false, showPulse: true, routePanel: false, compact: false, metrics: ['distance', 'movingTime', 'heartRate', 'elevation'] },
  { id: 'glass', name: 'Glass', description: 'Transparent · Karte', background: 'transparent', foreground: '#fff', muted: 'rgba(255,255,255,.7)', accent: '#B9F23E', transparent: true, showRoute: true, showPulse: true, routePanel: true, compact: false, metrics: ['distance', 'movingTime', 'heartRate'] },
  { id: 'minimal', name: 'Minimal', description: 'Transparent · kompakt', background: 'transparent', foreground: '#fff', muted: 'rgba(255,255,255,.72)', accent: '#fff', transparent: true, showRoute: false, showPulse: false, routePanel: false, compact: true, metrics: ['distance', 'movingTime', 'avgSpeed'] },
  { id: 'sunset', name: 'Sunset', description: 'Warm · Karte', background: 'radial-gradient(circle at 18% 15%, #FFCB70, transparent 30%), linear-gradient(145deg, #792F54, #D65745 58%, #EF9C55)', foreground: '#fff', muted: 'rgba(255,255,255,.7)', accent: '#FFE29D', transparent: false, showRoute: true, showPulse: false, routePanel: false, compact: false, metrics: ['distance', 'duration', 'elevation', 'avgSpeed'] },
  { id: 'pulse', name: 'Pulse', description: 'Puls im Fokus', background: 'linear-gradient(145deg, #2A0C18, #801D3B 60%, #D64D62)', foreground: '#fff', muted: 'rgba(255,255,255,.68)', accent: '#FF9AB0', transparent: false, showRoute: false, showPulse: true, routePanel: false, compact: false, metrics: ['heartRate', 'distance', 'movingTime', 'hydration'] },
  { id: 'topography', name: 'Topografie', description: 'Karte · viel Statistik', background: 'linear-gradient(145deg, #DDE6D6, #AABF9B)', foreground: '#17372C', muted: 'rgba(23,55,44,.62)', accent: '#F16B4E', transparent: false, showRoute: true, showPulse: true, routePanel: true, compact: false, metrics: ['distance', 'elevation', 'avgSpeed', 'heartRate', 'power', 'cadence'] },
  { id: 'electric', name: 'Electric', description: 'Sportlich · ohne Karte', background: 'linear-gradient(135deg, #071624 0 50%, #0B2A3E 50% 100%)', foreground: '#F6FEFF', muted: 'rgba(246,254,255,.6)', accent: '#00E5C4', transparent: false, showRoute: false, showPulse: false, routePanel: false, compact: false, metrics: ['distance', 'movingTime', 'avgSpeed', 'maxSpeed', 'power', 'cadence'] },
  { id: 'outline', name: 'Outline', description: 'Transparent · ohne Puls', background: 'transparent', foreground: '#fff', muted: 'rgba(255,255,255,.7)', accent: '#fff', transparent: true, showRoute: true, showPulse: false, routePanel: false, compact: true, metrics: ['distance', 'movingTime', 'elevation'] },
]

const METRIC_OPTIONS: { key: MetricKey; label: string }[] = [
  { key: 'distance', label: 'Distanz' },
  { key: 'movingTime', label: 'Fahrzeit' },
  { key: 'duration', label: 'Gesamtzeit' },
  { key: 'elevation', label: 'Höhenmeter' },
  { key: 'avgSpeed', label: 'Ø Tempo' },
  { key: 'maxSpeed', label: 'Max. Tempo' },
  { key: 'heartRate', label: 'Ø Puls' },
  { key: 'power', label: 'Ø Leistung' },
  { key: 'cadence', label: 'Ø Trittfrequenz' },
  { key: 'hydration', label: 'Trinkmenge' },
]

export function OverlayExportDialog({ open, onClose, activity, points }: { open: boolean; onClose: () => void; activity: Activity; points: TrackPoint[] }) {
  const exportRef = useRef<HTMLDivElement>(null)
  const [presetId, setPresetId] = useState(OVERLAY_PRESETS[0].id)
  const [metrics, setMetrics] = useState<MetricKey[]>(OVERLAY_PRESETS[0].metrics)
  const [showRoute, setShowRoute] = useState(OVERLAY_PRESETS[0].showRoute)
  const [showTitle, setShowTitle] = useState(true)
  const [showDate, setShowDate] = useState(true)
  const [showBrand, setShowBrand] = useState(true)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const preset = useMemo(() => OVERLAY_PRESETS.find((item) => item.id === presetId) ?? OVERLAY_PRESETS[0], [presetId])

  function selectPreset(next: OverlayPreset) {
    setPresetId(next.id)
    setMetrics(next.metrics)
    setShowRoute(next.showRoute)
  }

  function toggleMetric(key: MetricKey) {
    setMetrics((current) => current.includes(key) ? current.filter((item) => item !== key) : current.length < 6 ? [...current, key] : current)
  }

  async function exportImage() {
    if (!exportRef.current) return
    setPending(true)
    setError(null)
    try {
      const dataUrl = await toPng(exportRef.current, { cacheBust: true, pixelRatio: 2, quality: 1 })
      const link = document.createElement('a')
      link.download = `${activity.title.replace(/[^a-z0-9äöüß-]+/gi, '-').toLowerCase()}-${preset.id}.png`
      link.href = dataUrl
      link.click()
    } catch {
      setError('Das Overlay konnte nicht erzeugt werden. Bitte versuche es erneut.')
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={open} onClose={pending ? undefined : onClose} fullWidth maxWidth="lg">
      <DialogTitle>PNG-Overlay gestalten</DialogTitle>
      <DialogContent>
        <Typography color="text.secondary" sx={{ mb: 2.5 }}>Wähle eine Vorlage und passe Karte, Beschriftung und Kennzahlen für dein eigenes Overlay an.</Typography>

        <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1 }}>Design</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(5, 1fr)' }, gap: 1, mb: 3 }}>
          {OVERLAY_PRESETS.map((item) => (
            <Box
              component="button"
              type="button"
              key={item.id}
              aria-pressed={preset.id === item.id}
              onClick={() => selectPreset(item)}
              sx={{ border: '2px solid', borderColor: preset.id === item.id ? 'primary.main' : 'divider', borderRadius: 2.5, p: .75, bgcolor: 'background.paper', color: 'text.primary', textAlign: 'left', cursor: 'pointer', position: 'relative' }}
            >
              <Box sx={{
                height: 54,
                borderRadius: 1.5,
                background: item.background,
                backgroundColor: item.transparent ? '#DDE3E1' : undefined,
                backgroundImage: item.transparent
                  ? 'linear-gradient(45deg, #C7CFCC 25%, transparent 25%), linear-gradient(-45deg, #C7CFCC 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #C7CFCC 75%), linear-gradient(-45deg, transparent 75%, #C7CFCC 75%)'
                  : undefined,
                backgroundSize: item.transparent ? '12px 12px' : undefined,
                backgroundPosition: item.transparent ? '0 0, 0 6px, 6px -6px, -6px 0px' : undefined,
                position: 'relative',
                overflow: 'hidden',
              }}>
                {item.showRoute && <Box component="svg" viewBox="0 0 100 50" sx={{ width: '100%', height: '100%' }}><path d="M12 40 C 25 7, 42 43, 58 15 S 82 34, 91 9" fill="none" stroke={item.accent} strokeWidth="4" strokeLinecap="round" /></Box>}
              </Box>
              <Typography fontSize={12} fontWeight={800} mt={.6}>{item.name}</Typography>
              <Typography fontSize={9.5} color="text.secondary" noWrap>{item.description}</Typography>
              {preset.id === item.id && <CheckRoundedIcon color="primary" sx={{ position: 'absolute', top: 7, right: 7, fontSize: 18, bgcolor: 'background.paper', borderRadius: '50%' }} />}
            </Box>
          ))}
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) 580px' }, gap: 3, alignItems: 'start' }}>
          <Stack spacing={2.5}>
            <Box>
              <Stack direction="row" alignItems="center" gap={1} sx={{ mb: .5 }}><TuneRoundedIcon fontSize="small" /><Typography variant="subtitle2" fontWeight={800}>Inhalte</Typography></Stack>
              <FormControlLabel control={<Switch checked={showRoute} onChange={(event) => setShowRoute(event.target.checked)} />} label="Streckenkarte" disabled={!hasRoute(points)} />
              <FormControlLabel control={<Switch checked={showTitle} onChange={(event) => setShowTitle(event.target.checked)} />} label="Titel" />
              <FormControlLabel control={<Switch checked={showDate} onChange={(event) => setShowDate(event.target.checked)} />} label="Datum" />
              <FormControlLabel control={<Switch checked={showBrand} onChange={(event) => setShowBrand(event.target.checked)} />} label="Avento-Logo" />
            </Box>
            <Box>
              <Typography variant="subtitle2" fontWeight={800}>Kennzahlen</Typography>
              <Typography variant="caption" color="text.secondary">Bis zu sechs auswählen</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', mt: .75 }}>
                {METRIC_OPTIONS.map((option) => (
                  <FormControlLabel
                    key={option.key}
                    control={<Checkbox size="small" checked={metrics.includes(option.key)} onChange={() => toggleMetric(option.key)} disabled={!metrics.includes(option.key) && metrics.length >= 6} />}
                    label={<Typography variant="body2">{option.label}</Typography>}
                  />
                ))}
              </Box>
              {preset.showPulse && activity.avg_hr_bpm == null && <Alert severity="info" sx={{ mt: 1 }}>Für diese Aktivität sind keine Pulsdaten vorhanden.</Alert>}
            </Box>
          </Stack>

          <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle2" fontWeight={800}>Vorschau</Typography>
              {preset.transparent && <Chip size="small" label="Transparenter Hintergrund" />}
            </Stack>
            <Box sx={{ overflow: 'auto', borderRadius: 3, p: 2, backgroundColor: '#DDE3E1', backgroundImage: 'linear-gradient(45deg, #C9D0CE 25%, transparent 25%), linear-gradient(-45deg, #C9D0CE 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #C9D0CE 75%), linear-gradient(-45deg, transparent 75%, #C9D0CE 75%)', backgroundSize: '24px 24px', backgroundPosition: '0 0, 0 12px, 12px -12px, -12px 0px' }}>
              <OverlayCanvas ref={exportRef} activity={activity} points={points} preset={preset} metrics={metrics} showRoute={showRoute} showTitle={showTitle} showDate={showDate} showBrand={showBrand} />
            </Box>
          </Box>
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} color="inherit">Schließen</Button>
        <Button variant="contained" startIcon={<DownloadRoundedIcon />} disabled={pending} onClick={exportImage}>
          {pending ? 'PNG wird erstellt …' : 'PNG herunterladen'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

const OverlayCanvas = forwardRef<HTMLDivElement, { activity: Activity; points: TrackPoint[]; preset: OverlayPreset; metrics: MetricKey[]; showRoute: boolean; showTitle: boolean; showDate: boolean; showBrand: boolean }>(function OverlayCanvas({ activity, points, preset, metrics, showRoute, showTitle, showDate, showBrand }, ref) {
  const visibleMetrics = metrics.map((key) => metricValue(key, activity))
  return (
    <Box data-testid="overlay-canvas" ref={ref} sx={{ width: 540, height: 540, position: 'relative', overflow: 'hidden', p: preset.compact ? 4 : 4.5, color: preset.foreground, background: preset.background, fontFamily: 'Manrope Variable, sans-serif' }}>
      {!preset.transparent && <><Box sx={{ position: 'absolute', width: 290, height: 290, borderRadius: '50%', border: `48px solid ${preset.muted}`, opacity: .1, right: -140, bottom: -115 }} /><Box sx={{ position: 'absolute', width: 130, height: 130, borderRadius: '50%', bgcolor: preset.accent, opacity: .1, left: -55, top: 90 }} /></>}
      <Stack sx={{ height: '100%', position: 'relative', zIndex: 1 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" minHeight={30}>
          {showBrand ? <Typography fontWeight={900} fontSize={23} letterSpacing="-.06em">avento</Typography> : <span />}
          {showDate && <Typography fontWeight={700} fontSize={14} color={preset.muted}>{formatDate(activity.started_at)}</Typography>}
        </Stack>

        {showRoute ? (
          <Box sx={{ flex: 1, display: 'grid', placeItems: 'center', minHeight: 0, my: 1.25, borderRadius: 5, bgcolor: preset.routePanel ? 'rgba(255,255,255,.09)' : 'transparent', border: preset.routePanel ? `1px solid ${preset.muted}` : 0 }}>
            <RouteSketch points={points} color={preset.foreground} accent={preset.accent} compact={preset.compact} />
          </Box>
        ) : (
          <Box sx={{ flex: 1, display: 'flex', alignItems: 'flex-end', minHeight: 100, pb: 2 }}>
            {preset.showPulse && activity.avg_hr_bpm != null && <Stack direction="row" alignItems="center" gap={1.2} color={preset.accent}><FavoriteRoundedIcon sx={{ fontSize: 52 }} /><Typography fontSize={64} fontWeight={900} lineHeight={1}>{Math.round(activity.avg_hr_bpm)}</Typography><Typography fontSize={16} fontWeight={800}>bpm</Typography></Stack>}
          </Box>
        )}

        {showTitle && <Typography fontWeight={900} fontSize={preset.compact ? 23 : 27} lineHeight={1.15} noWrap sx={{ mb: 2 }}>{activity.title}</Typography>}
        {visibleMetrics.length > 0 && <Box sx={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(visibleMetrics.length, 3)}, 1fr)`, gap: 1.5, borderTop: `1px solid ${preset.muted}`, pt: 2 }}>
          {visibleMetrics.map((metric) => <OverlayMetric key={metric.label} label={metric.label} value={metric.value} muted={preset.muted} accent={metric.key === 'heartRate' ? preset.accent : preset.foreground} />)}
        </Box>}
      </Stack>
    </Box>
  )
})

function metricValue(key: MetricKey, activity: Activity) {
  const values: Record<MetricKey, { key: MetricKey; label: string; value: string }> = {
    distance: { key, label: 'Distanz', value: formatDistance(activity.distance_m) },
    movingTime: { key, label: 'Fahrzeit', value: compactDuration(activity.moving_time_s) },
    duration: { key, label: 'Gesamtzeit', value: compactDuration(activity.duration_s) },
    elevation: { key, label: 'Höhe', value: formatElevation(activity.elevation_gain_m) },
    avgSpeed: { key, label: 'Ø Tempo', value: formatSpeedMps(activity.avg_speed_mps) },
    maxSpeed: { key, label: 'Max. Tempo', value: formatSpeedMps(activity.max_speed_mps) },
    heartRate: { key, label: 'Ø Puls', value: formatHeartRate(activity.avg_hr_bpm) },
    power: { key, label: 'Ø Leistung', value: activity.avg_power_w == null ? '–' : `${Math.round(activity.avg_power_w)} W` },
    cadence: { key, label: 'Ø Trittfrequenz', value: activity.avg_cadence_rpm == null ? '–' : `${Math.round(activity.avg_cadence_rpm)} rpm` },
    hydration: { key, label: 'Trinkmenge', value: formatHydration(activity.hydration_ml) },
  }
  return values[key]
}

function compactDuration(seconds: number) {
  return formatDuration(seconds).replace(' Std. ', ':').replace(' Min.', '').replace(' Sek.', ' s')
}

function OverlayMetric({ label, value, muted, accent }: { label: string; value: string; muted: string; accent: string }) {
  return <Box sx={{ minWidth: 0 }}><Typography fontSize={10.5} fontWeight={800} color={muted} textTransform="uppercase" letterSpacing=".06em" noWrap>{label}</Typography><Typography fontSize={15} fontWeight={900} mt={.25} color={accent} noWrap>{value}</Typography></Box>
}

function hasRoute(points: TrackPoint[]) {
  return points.filter((point) => typeof point.longitude === 'number' && typeof point.latitude === 'number').length >= 2
}

function RouteSketch({ points, color, accent, compact }: { points: TrackPoint[]; color: string; accent: string; compact: boolean }) {
  const gps = points.filter((point): point is TrackPoint & { longitude: number; latitude: number } => typeof point.longitude === 'number' && typeof point.latitude === 'number')
  if (gps.length < 2) return <Stack alignItems="center" color="inherit" sx={{ opacity: .42 }}><RouteRoundedIcon sx={{ fontSize: 90 }} /><Typography>Indoor-Aktivität</Typography></Stack>
  const minX = Math.min(...gps.map((point) => point.longitude))
  const maxX = Math.max(...gps.map((point) => point.longitude))
  const minY = Math.min(...gps.map((point) => point.latitude))
  const maxY = Math.max(...gps.map((point) => point.latitude))
  const width = Math.max(maxX - minX, .000001)
  const height = Math.max(maxY - minY, .000001)
  const sampled = gps.filter((_, index) => index % Math.max(1, Math.ceil(gps.length / 300)) === 0)
  const coords = sampled.map((point) => ({ x: 20 + ((point.longitude - minX) / width) * 320, y: 240 - ((point.latitude - minY) / height) * 210 }))
  const coordinates = coords.map(({ x, y }) => `${x},${y}`).join(' ')
  return (
    <Box component="svg" viewBox="0 0 360 260" sx={{ width: compact ? 315 : 350, height: compact ? 225 : 250, filter: 'drop-shadow(0 8px 14px rgba(0,0,0,.2))' }}>
      <polyline points={coordinates} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={coords[0].x} cy={coords[0].y} r="8" fill={accent} stroke={color} strokeWidth="3" />
      <circle cx={coords.at(-1)!.x} cy={coords.at(-1)!.y} r="7" fill={color} stroke={accent} strokeWidth="3" />
    </Box>
  )
}
