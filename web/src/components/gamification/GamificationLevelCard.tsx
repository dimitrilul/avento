import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import FlagRoundedIcon from '@mui/icons-material/FlagRounded'
import LockPersonRoundedIcon from '@mui/icons-material/LockPersonRounded'
import MilitaryTechRoundedIcon from '@mui/icons-material/MilitaryTechRounded'
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Stack,
  Typography,
  useTheme,
} from '@mui/material'
import type { GamificationOverview } from '../../api'
import { formatXp } from './gamificationFormat'

export function GamificationLevelCard({ overview }: { overview: GamificationOverview }) {
  const theme = useTheme()
  const unlockedBadges = overview.badges.filter((badge) => badge.unlocked).length
  const activeGoals = overview.goals.filter((goal) => goal.status === 'active').length

  return (
    <Card
      sx={{
        overflow: 'hidden',
        background: `radial-gradient(circle at 8% 8%, ${alpha(theme.palette.secondary.main, .22)}, transparent 28%), radial-gradient(circle at 92% 8%, ${alpha(theme.palette.primary.main, .22)}, transparent 34%), linear-gradient(145deg, ${alpha(theme.palette.primary.main, .08)}, ${theme.palette.background.paper} 68%)`,
      }}
    >
      <CardContent sx={{ p: { xs: 2.5, sm: 3.5 }, '&:last-child': { pb: { xs: 2.5, sm: 3.5 } } }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={{ xs: 3, md: 4 }} alignItems={{ xs: 'stretch', md: 'center' }}>
          <Stack direction="row" spacing={2.25} alignItems="center" sx={{ minWidth: { md: 330 } }}>
            <Box sx={{ position: 'relative', display: 'inline-flex', flex: 'none' }}>
              <CircularProgress
                variant="determinate"
                value={overview.level.progress_percent}
                size={92}
                thickness={4.5}
                color="secondary"
                aria-label={`${Math.round(overview.level.progress_percent)} Prozent bis zum nächsten Level`}
              />
              <Box sx={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" fontWeight={800} display="block">LEVEL</Typography>
                  <Typography variant="h3" lineHeight={1}>{overview.level.level}</Typography>
                </Box>
              </Box>
            </Box>
            <Box minWidth={0}>
              <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
                <Typography component="h2" variant="h2">{overview.level.name}</Typography>
                <Chip size="small" icon={<LockPersonRoundedIcon />} label="Nur für dich" variant="outlined" />
              </Stack>
              <Typography color="text.secondary" sx={{ mt: .5 }}>
                Persönlicher Fortschritt ohne Rangliste oder Vergleichsdruck.
              </Typography>
            </Box>
          </Stack>

          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="baseline" gap={2}>
              <Typography fontWeight={800}>{formatXp(overview.level.current_xp)}</Typography>
              <Typography variant="body2" color="text.secondary">von {formatXp(overview.level.next_level_xp)}</Typography>
            </Stack>
            <LinearProgress
              variant="determinate"
              value={overview.level.progress_percent}
              aria-label="XP-Fortschritt"
              sx={{ height: 10, borderRadius: 999, mt: 1 }}
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
              <Stat icon={<AutoAwesomeRoundedIcon />} label="Gesamt" value={formatXp(overview.level.total_xp)} />
              <Stat icon={<FlagRoundedIcon />} label="Aktive Ziele" value={String(activeGoals)} />
              <Stat icon={<MilitaryTechRoundedIcon />} label="Abzeichen" value={`${unlockedBadges}/${overview.badges.length}`} />
            </Stack>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  )
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Stack
      direction="row"
      spacing={1}
      alignItems="center"
      sx={{
        flex: 1,
        p: 1.25,
        minWidth: 0,
        borderRadius: 2.5,
        bgcolor: (theme) => alpha(theme.palette.background.paper, .64),
        border: '1px solid',
        borderColor: 'divider',
        '& svg': { color: 'primary.main', fontSize: 20 },
      }}
    >
      <>{icon}</>
      <Box minWidth={0}>
        <Typography variant="caption" color="text.secondary" display="block" noWrap>{label}</Typography>
        <Typography variant="body2" fontWeight={800} noWrap>{value}</Typography>
      </Box>
    </Stack>
  )
}

