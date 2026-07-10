import { useTheme } from '@mui/material'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { TrendPoint } from '../api'

export function TrendChart({ data }: { data: TrendPoint[] }) {
  const theme = useTheme()
  const formatted = data.map((point) => ({
    ...point,
    distance_km: point.distance_m / 1000,
    label: new Intl.DateTimeFormat('de-DE', { month: 'short', year: '2-digit' }).format(new Date(`${point.month}-01T12:00:00`)),
  }))
  return (
    <ResponsiveContainer width="100%" height={290}>
      <AreaChart data={formatted} margin={{ top: 12, right: 6, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="distanceFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={theme.palette.primary.main} stopOpacity={.32} />
            <stop offset="100%" stopColor={theme.palette.primary.main} stopOpacity={.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={theme.palette.divider} />
        <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: theme.palette.text.secondary, fontSize: 12 }} />
        <YAxis width={54} unit=" km" axisLine={false} tickLine={false} tick={{ fill: theme.palette.text.secondary, fontSize: 12 }} />
        <Tooltip
          formatter={(value) => [`${Number(value).toLocaleString('de-DE', { maximumFractionDigits: 1 })} km`, 'Distanz']}
          contentStyle={{ borderRadius: 14, border: `1px solid ${theme.palette.divider}`, boxShadow: '0 12px 30px rgba(20,50,45,.08)' }}
        />
        <Area type="monotone" dataKey="distance_km" stroke={theme.palette.primary.main} strokeWidth={3} fill="url(#distanceFill)" activeDot={{ r: 5 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
