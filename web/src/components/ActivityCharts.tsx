import { Box, Card, CardContent, Stack, Typography, useTheme } from '@mui/material'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TrackPoint } from '../api'
import { EmptyState } from './States'

function sample(points: TrackPoint[], maximum = 500) {
  if (points.length <= maximum) return points
  const step = Math.ceil(points.length / maximum)
  return points.filter((_, index) => index % step === 0 || index === points.length - 1)
}

export function ActivityCharts({ points }: { points: TrackPoint[] }) {
  const theme = useTheme()
  const data = sample(points).map((point, index) => ({
    index,
    distance: (point.distance_m ?? 0) / 1000,
    elevation: point.altitude_m,
    speed: point.speed_mps == null ? null : point.speed_mps * 3.6,
    heartRate: point.heart_rate_bpm,
    power: point.power_w,
    cadence: point.cadence_rpm,
  }))
  if (!data.length) return <EmptyState title="Keine Diagrammdaten" description="In dieser TCX-Datei sind keine Messpunkte enthalten." />
  const hasPerformance = data.some((point) => point.heartRate != null || point.power != null || point.cadence != null)
  const xKey = data.some((point) => point.distance > 0) ? 'distance' : 'index'

  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2.5 }}>
      <Card>
        <CardContent sx={{ p: 2.5 }}>
          <Stack sx={{ mb: 1 }}>
            <Typography variant="h3">Höhe & Tempo</Typography>
            <Typography variant="body2" color="text.secondary">Streckenverlauf in Kilometern</Typography>
          </Stack>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data} margin={{ top: 18, right: 8, left: -14, bottom: 0 }}>
              <defs>
                <linearGradient id="elevationFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={theme.palette.chart.lime} stopOpacity={.55} /><stop offset="1" stopColor={theme.palette.chart.lime} stopOpacity={.04} /></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={theme.palette.divider} />
              <XAxis dataKey={xKey} unit={xKey === 'distance' ? ' km' : ''} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
              <YAxis yAxisId="elevation" unit=" m" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
              <YAxis yAxisId="speed" orientation="right" unit=" km/h" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
              <Tooltip labelFormatter={(value) => xKey === 'distance' ? `${Number(value).toLocaleString('de-DE', { maximumFractionDigits: 1 })} km` : `Messpunkt ${value}`} />
              <Legend />
              <Area yAxisId="elevation" type="monotone" dataKey="elevation" name="Höhe (m)" stroke={theme.palette.chart.lime} strokeWidth={2} fill="url(#elevationFill)" connectNulls />
              <Line yAxisId="speed" type="monotone" dataKey="speed" name="Tempo (km/h)" stroke={theme.palette.chart.blue} strokeWidth={2} dot={false} connectNulls />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card>
        <CardContent sx={{ p: 2.5 }}>
          <Stack sx={{ mb: 1 }}>
            <Typography variant="h3">Leistung</Typography>
            <Typography variant="body2" color="text.secondary">Herzfrequenz, Watt und Kadenz</Typography>
          </Stack>
          {hasPerformance ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data} margin={{ top: 18, right: 8, left: -14, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={theme.palette.divider} />
                <XAxis dataKey={xKey} unit={xKey === 'distance' ? ' km' : ''} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="heartRate" name="Herzfrequenz (bpm)" stroke={theme.palette.chart.coral} dot={false} strokeWidth={2} connectNulls />
                <Line type="monotone" dataKey="power" name="Leistung (W)" stroke={theme.palette.chart.amber} dot={false} strokeWidth={2} connectNulls />
                <Line type="monotone" dataKey="cadence" name="Kadenz (rpm)" stroke={theme.palette.chart.teal} dot={false} strokeWidth={2} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Stack justifyContent="center" sx={{ height: 300 }}><EmptyState title="Keine Sensordaten" description="Herzfrequenz, Leistung und Kadenz wurden nicht aufgezeichnet." /></Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}
