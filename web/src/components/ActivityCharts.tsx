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
    distance: Math.round(((point.distance_m ?? 0) / 1000) * 100) / 100,
    elevation: point.altitude_m == null ? null : Math.round(point.altitude_m * 10) / 10,
    speed: point.speed_mps == null ? null : Math.round(point.speed_mps * 36) / 10,
    heartRate: point.heart_rate_bpm,
  }))
  if (!data.length) return <EmptyState title="Keine Diagrammdaten" description="In dieser TCX-Datei sind keine Messpunkte enthalten." />
  const hasHeartRate = data.some((point) => point.heartRate != null)
  const xKey = data.some((point) => point.distance > 0) ? 'distance' : 'index'
  const formatXAxis = (value: number) => xKey === 'distance'
    ? Number(value).toLocaleString('de-DE', { maximumFractionDigits: 1 })
    : String(Math.round(value))
  const formatLabel = (value: number) => xKey === 'distance'
    ? `${formatXAxis(value)} km`
    : `Messpunkt ${Math.round(value)}`

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
              <XAxis dataKey={xKey} type="number" domain={['dataMin', 'dataMax']} tickCount={7} unit={xKey === 'distance' ? ' km' : ''} tickFormatter={formatXAxis} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
              <YAxis yAxisId="elevation" unit=" m" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
              <YAxis yAxisId="speed" orientation="right" unit=" km/h" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
              <Tooltip labelFormatter={(value) => formatLabel(Number(value))} />
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
            <Typography variant="h3">Herzfrequenz</Typography>
            <Typography variant="body2" color="text.secondary">Verlauf entlang der Strecke</Typography>
          </Stack>
          {hasHeartRate ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data} margin={{ top: 18, right: 8, left: -14, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={theme.palette.divider} />
                <XAxis dataKey={xKey} type="number" domain={['dataMin', 'dataMax']} tickCount={7} unit={xKey === 'distance' ? ' km' : ''} tickFormatter={formatXAxis} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                <Tooltip labelFormatter={(value) => formatLabel(Number(value))} />
                <Legend />
                <Line type="monotone" dataKey="heartRate" name="Herzfrequenz (bpm)" stroke={theme.palette.chart.coral} dot={false} strokeWidth={2} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Stack justifyContent="center" sx={{ height: 300 }}><EmptyState title="Keine Herzfrequenzdaten" description="Für diese Aktivität wurde keine Herzfrequenz aufgezeichnet." /></Stack>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}
