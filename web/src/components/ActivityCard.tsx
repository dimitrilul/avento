import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded'
import { Avatar, Box, Card, CardActionArea, Chip, Divider, Stack, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import type { Activity } from '../api'
import { activityTypeLabels, formatDateTime, formatDistance, formatDuration, formatElevation, formatSpeedMps } from '../utils/format'

export function ActivityCard({ activity, selected, onSelect }: { activity: Activity; selected?: boolean; onSelect?: (activity: Activity) => void }) {
  const navigate = useNavigate()
  return (
    <Card sx={{ outline: selected ? '2px solid' : 'none', outlineColor: 'primary.main', transition: 'transform 150ms ease, box-shadow 150ms ease', '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 16px 38px rgba(20,50,45,.09)' } }}>
      <CardActionArea
        onClick={() => onSelect ? onSelect(activity) : navigate(`/aktivitaeten/${activity.id}`)}
        sx={{ p: 2.25 }}
      >
        <Stack direction="row" gap={2} alignItems="flex-start">
          <Avatar variant="rounded" sx={{ width: 52, height: 52, borderRadius: 3, bgcolor: 'primary.main', color: 'white' }}>
            <RouteRoundedIcon />
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Stack direction="row" justifyContent="space-between" gap={1} alignItems="flex-start">
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="h4" noWrap>{activity.title}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: .35 }}>{formatDateTime(activity.started_at)}</Typography>
              </Box>
              <Stack direction="row" gap={.5} alignItems="center">
                {(activity.data_quality_flags?.some((flag) => flag.severity === 'warning' || flag.severity === 'error')) && <Chip size="small" color="warning" label="Daten prüfen" />}
                {activity.include_in_statistics === false && <Chip size="small" variant="outlined" label="Nicht in Statistik" />}
                <Chip size="small" label={activityTypeLabels[activity.type] ?? activity.type} />
              </Stack>
            </Stack>
            <Divider sx={{ my: 1.75 }} />
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 1.25 }}>
              <MiniMetric icon={<RouteRoundedIcon />} value={formatDistance(activity.distance_m)} />
              <MiniMetric icon={<AccessTimeRoundedIcon />} value={formatDuration(activity.moving_time_s)} />
              <MiniMetric icon={<LandscapeRoundedIcon />} value={formatElevation(activity.elevation_gain_m)} />
              <MiniMetric icon={<SpeedRoundedIcon />} value={formatSpeedMps(activity.avg_speed_mps)} />
            </Box>
          </Box>
        </Stack>
      </CardActionArea>
    </Card>
  )
}

function MiniMetric({ icon, value }: { icon: React.ReactNode; value: string }) {
  return <Stack direction="row" alignItems="center" spacing={.75} color="text.secondary" sx={{ '& svg': { fontSize: 18 } }}><>{icon}</><Typography variant="body2" fontWeight={650} color="text.primary">{value}</Typography></Stack>
}
