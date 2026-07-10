import { useRef, useState } from 'react'
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import ShareRoundedIcon from '@mui/icons-material/ShareRounded'
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from '@mui/material'
import { toPng } from 'html-to-image'
import type { Activity, TrackPoint } from '../api'
import { formatDate, formatDistance, formatDuration, formatElevation, formatSpeedMps } from '../utils/format'

export function OverlayExportDialog({ open, onClose, activity, points }: { open: boolean; onClose: () => void; activity: Activity; points: TrackPoint[] }) {
  const exportRef = useRef<HTMLDivElement>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function exportImage() {
    if (!exportRef.current) return
    setPending(true)
    setError(null)
    try {
      const dataUrl = await toPng(exportRef.current, { cacheBust: true, pixelRatio: 2, quality: 1 })
      const link = document.createElement('a')
      link.download = `${activity.title.replace(/[^a-z0-9äöüß-]+/gi, '-').toLowerCase()}-avento.png`
      link.href = dataUrl
      link.click()
    } catch {
      setError('Das Overlay konnte nicht erzeugt werden. Bitte versuche es erneut.')
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={open} onClose={pending ? undefined : onClose} fullWidth maxWidth="md">
      <DialogTitle>Share-Overlay</DialogTitle>
      <DialogContent>
        <Typography color="text.secondary" sx={{ mb: 2 }}>Exportiere deine Fahrt als quadratisches PNG für Messenger und soziale Medien.</Typography>
        <Box sx={{ overflow: 'auto', borderRadius: 4, bgcolor: '#E9EEEA', p: { xs: 1, sm: 3 } }}>
          <Box
            ref={exportRef}
            sx={{
              width: 540,
              height: 540,
              maxWidth: 'none',
              position: 'relative',
              overflow: 'hidden',
              p: 4,
              color: 'white',
              background: 'radial-gradient(circle at 85% 12%, rgba(165,200,56,.58), transparent 31%), linear-gradient(145deg, #072F2F 0%, #0E6562 72%, #397A53 100%)',
            }}
          >
            <Box sx={{ position: 'absolute', width: 280, height: 280, borderRadius: '50%', border: '48px solid rgba(255,255,255,.045)', right: -130, bottom: -100 }} />
            <Stack sx={{ height: '100%', position: 'relative', zIndex: 1 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography fontWeight={850} fontSize={24} letterSpacing="-.05em">avento</Typography>
                <Typography fontWeight={650} color="rgba(255,255,255,.68)">{formatDate(activity.started_at)}</Typography>
              </Stack>
              <Box sx={{ flex: 1, display: 'grid', placeItems: 'center', minHeight: 0, py: 1 }}>
                <RouteSketch points={points} />
              </Box>
              <Typography fontWeight={800} fontSize={26} noWrap sx={{ mb: 2 }}>{activity.title}</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1.5, borderTop: '1px solid rgba(255,255,255,.18)', pt: 2 }}>
                <OverlayMetric label="Distanz" value={formatDistance(activity.distance_m)} />
                <OverlayMetric label="Fahrzeit" value={formatDuration(activity.moving_time_s).replace(' Std. ', ':').replace(' Min.', '')} />
                <OverlayMetric label="Höhe" value={formatElevation(activity.elevation_gain_m)} />
                <OverlayMetric label="Ø Tempo" value={formatSpeedMps(activity.avg_speed_mps)} />
              </Box>
            </Stack>
          </Box>
        </Box>
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} color="inherit">Schließen</Button>
        <Button variant="contained" startIcon={pending ? <ShareRoundedIcon /> : <DownloadRoundedIcon />} disabled={pending} onClick={exportImage}>
          {pending ? 'PNG wird erstellt …' : 'PNG herunterladen'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

function OverlayMetric({ label, value }: { label: string; value: string }) {
  return <Box><Typography fontSize={11} fontWeight={700} color="rgba(255,255,255,.62)" textTransform="uppercase" letterSpacing=".06em">{label}</Typography><Typography fontSize={15} fontWeight={800} mt={.3}>{value}</Typography></Box>
}

function RouteSketch({ points }: { points: TrackPoint[] }) {
  const gps = points.filter((point): point is TrackPoint & { longitude: number; latitude: number } => typeof point.longitude === 'number' && typeof point.latitude === 'number')
  if (gps.length < 2) return <Stack alignItems="center" color="rgba(255,255,255,.38)"><RouteRoundedIcon sx={{ fontSize: 110 }} /><Typography>Indoor-Aktivität</Typography></Stack>
  const minX = Math.min(...gps.map((point) => point.longitude))
  const maxX = Math.max(...gps.map((point) => point.longitude))
  const minY = Math.min(...gps.map((point) => point.latitude))
  const maxY = Math.max(...gps.map((point) => point.latitude))
  const width = Math.max(maxX - minX, .000001)
  const height = Math.max(maxY - minY, .000001)
  const sampled = gps.filter((_, index) => index % Math.max(1, Math.ceil(gps.length / 300)) === 0)
  const coordinates = sampled.map((point) => `${20 + ((point.longitude - minX) / width) * 320},${240 - ((point.latitude - minY) / height) * 210}`).join(' ')
  return (
    <Box component="svg" viewBox="0 0 360 260" sx={{ width: 360, height: 260, filter: 'drop-shadow(0 8px 14px rgba(0,0,0,.18))' }}>
      <polyline points={coordinates} fill="none" stroke="rgba(255,255,255,.95)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={coordinates.split(' ')[0]?.split(',')[0]} cy={coordinates.split(' ')[0]?.split(',')[1]} r="8" fill="#A5C838" stroke="white" strokeWidth="3" />
    </Box>
  )
}
