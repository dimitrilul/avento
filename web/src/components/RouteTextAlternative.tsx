import { Box, List, ListItem, ListItemText, Typography } from '@mui/material'
import type { TrackPoint } from '../api'

export function RouteTextAlternative({ points }: { points: TrackPoint[] }) {
  const located = points.filter((point) => point.latitude != null && point.longitude != null)
  if (!located.length) return <Typography variant="body2" color="text.secondary">Für diese Aktivität liegen keine Ortsdaten für eine Streckenliste vor.</Typography>
  const events = located.filter((_, index) => index === 0 || index === located.length - 1 || index % Math.max(1, Math.ceil(located.length / 12)) === 0)
  return (
    <Box component="section" aria-label="Textalternative zur Karte" sx={{ mt: 1.5 }}>
      <Typography variant="h4">Textalternative zur Karte</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>
        {located.length} GPS-Punkte · Start {located[0].latitude?.toFixed(5)}, {located[0].longitude?.toFixed(5)} · Ende {located.at(-1)?.latitude?.toFixed(5)}, {located.at(-1)?.longitude?.toFixed(5)}
      </Typography>
      <List dense disablePadding sx={{ mt: 1 }}>
        {events.map((point, index) => <ListItem key={`${point.time}-${index}`} disableGutters><ListItemText primary={`${point.distance_m == null ? `Ereignis ${index + 1}` : `${(point.distance_m / 1000).toLocaleString('de-DE', { maximumFractionDigits: 1 })} km`}`} secondary={`Koordinate ${point.latitude?.toFixed(5)}, ${point.longitude?.toFixed(5)}${point.altitude_m == null ? '' : ` · ${Math.round(point.altitude_m)} m Höhe`}`} /></ListItem>)}
      </List>
    </Box>
  )
}
