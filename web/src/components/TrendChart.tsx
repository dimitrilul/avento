import { useId } from 'react'
import { Box, Table, TableBody, TableCell, TableHead, TableRow, useTheme } from '@mui/material'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export function TrendChart({ data }: { data: Array<{ label: string; distance_km: number }> }) {
  const theme = useTheme()
  const gradientId = `distance-fill-${useId().replaceAll(':', '')}`
  return (
    <Box component="section" aria-label="Distanzverlauf">
      <Box component="details" sx={{ mb: 1.5 }}>
        <Box component="summary" sx={{ cursor: 'pointer', color: 'text.secondary', typography: 'caption' }}>Tabellarische Ansicht anzeigen</Box>
        <Table size="small" aria-label="Tabellarischer Distanzverlauf"><TableHead><TableRow><TableCell>Zeitraum</TableCell><TableCell align="right">Distanz</TableCell></TableRow></TableHead><TableBody>{data.map((point) => <TableRow key={point.label}><TableCell>{point.label}</TableCell><TableCell align="right">{point.distance_km.toLocaleString('de-DE', { maximumFractionDigits: 1 })} km</TableCell></TableRow>)}</TableBody></Table>
      </Box>
      <ResponsiveContainer width="100%" height={310}>
        <AreaChart data={data} margin={{ top: 12, right: 6, bottom: 0, left: -8 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={theme.palette.primary.main} stopOpacity={.42} />
            <stop offset="72%" stopColor={theme.palette.primary.main} stopOpacity={.08} />
            <stop offset="100%" stopColor={theme.palette.primary.main} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 6" vertical={false} stroke={theme.palette.divider} />
        <XAxis dataKey="label" axisLine={false} tickLine={false} minTickGap={22} tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} />
        <YAxis width={52} unit=" km" axisLine={false} tickLine={false} tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} />
        <Tooltip cursor={{ stroke: theme.palette.primary.main, strokeDasharray: '4 4' }} formatter={(value) => [`${Number(value).toLocaleString('de-DE', { maximumFractionDigits: 1 })} km`, 'Distanz']} contentStyle={{ background: theme.palette.background.paper, color: theme.palette.text.primary, borderRadius: 14, border: `1px solid ${theme.palette.divider}`, boxShadow: '0 16px 34px rgba(0,0,0,.2)' }} />
        <Area type="monotone" dataKey="distance_km" stroke={theme.palette.primary.main} strokeWidth={3} fill={`url(#${gradientId})`} activeDot={{ r: 5, strokeWidth: 3, fill: theme.palette.background.paper }} />
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  )
}
