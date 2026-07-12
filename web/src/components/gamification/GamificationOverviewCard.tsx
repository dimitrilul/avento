import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded'
import FlagRoundedIcon from '@mui/icons-material/FlagRounded'
import LocalFireDepartmentRoundedIcon from '@mui/icons-material/LocalFireDepartmentRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import StarsRoundedIcon from '@mui/icons-material/StarsRounded'
import {
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  LinearProgress,
  Skeleton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Link as RouterLink } from 'react-router-dom'
import { gamificationApi, gamificationOverviewQueryKey } from '../../api'
import { formatGamificationValue } from './gamificationFormat'

export function GamificationOverviewCard() {
  const overview = useQuery({
    queryKey: gamificationOverviewQueryKey,
    queryFn: gamificationApi.overview,
  })
  const activeGoal = overview.data?.goals.find((goal) => goal.status === 'active')

  return (
    <Card
      sx={{
        height: '100%',
        gridColumn: { md: 'span 2', xl: 'span 2' },
        background: (theme) => `linear-gradient(140deg, ${alpha(theme.palette.secondary.main, .12)}, ${theme.palette.background.paper} 58%)`,
      }}
    >
      <CardContent sx={{ p: 2.25, '&:last-child': { pb: 2.25 }, height: '100%' }}>
        <Stack height="100%" spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
            <Box>
              <Typography variant="overline" color="primary.main" fontWeight={800}>DEINE MEILENSTEINE</Typography>
              <Typography variant="h4">Persönlicher Fortschritt</Typography>
            </Box>
            <Box sx={{ width: 40, height: 40, borderRadius: 2.5, display: 'grid', placeItems: 'center', bgcolor: 'secondary.light', color: 'secondary.dark' }}>
              <StarsRoundedIcon />
            </Box>
          </Stack>

          {overview.isLoading ? (
            <Stack spacing={1.25}>
              <Skeleton width="46%" />
              <Skeleton variant="rounded" height={9} />
              <Skeleton width="70%" />
            </Stack>
          ) : overview.isError || !overview.data ? (
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1} sx={{ flex: 1 }}>
              <Typography variant="body2" color="text.secondary">Dein Fortschritt ist gerade nicht erreichbar.</Typography>
              <Tooltip title="Erneut versuchen">
                <IconButton aria-label="Gamification-Fortschritt erneut laden" onClick={() => void overview.refetch()}><RefreshRoundedIcon /></IconButton>
              </Tooltip>
            </Stack>
          ) : (
            <>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 1.5, sm: 2.5 }} alignItems={{ xs: 'stretch', sm: 'center' }}>
                <Box sx={{ minWidth: { sm: 150 } }}>
                  <Stack direction="row" alignItems="baseline" gap={.75}>
                    <Typography variant="h3">Level {overview.data.level.level}</Typography>
                    <Typography variant="body2" color="text.secondary" noWrap>{overview.data.level.name}</Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={overview.data.level.progress_percent}
                    aria-label="XP-Fortschritt im Dashboard"
                    sx={{ mt: .75, height: 7, borderRadius: 999 }}
                  />
                </Box>
                <Stack direction="row" spacing={1} sx={{ flex: 1 }}>
                  <MiniStat icon={<LocalFireDepartmentRoundedIcon />} value={`${overview.data.streak.current_weeks}`} label={overview.data.streak.current_weeks === 1 ? 'Woche' : 'Wochen'} />
                  <MiniStat icon={<FlagRoundedIcon />} value={`${overview.data.goals.filter((goal) => goal.status === 'active').length}`} label="Ziele" />
                </Stack>
              </Stack>
              {activeGoal && (
                <Box sx={{ p: 1.25, borderRadius: 2.5, bgcolor: 'action.hover' }}>
                  <Stack direction="row" justifyContent="space-between" gap={1}>
                    <Typography variant="body2" fontWeight={750} noWrap>{activeGoal.title}</Typography>
                    <Typography variant="caption" color="text.secondary" whiteSpace="nowrap">
                      {formatGamificationValue(activeGoal.metric, activeGoal.current_value, activeGoal.unit)}
                    </Typography>
                  </Stack>
                  <LinearProgress variant="determinate" value={activeGoal.progress_percent} aria-label={`Fortschritt für ${activeGoal.title}`} sx={{ mt: .75, height: 5, borderRadius: 999 }} />
                </Box>
              )}
            </>
          )}

          <Button component={RouterLink} to="/meilensteine" endIcon={<ArrowForwardRoundedIcon />} sx={{ alignSelf: 'flex-start', px: 0, mt: 'auto !important' }}>
            Alle Meilensteine
          </Button>
        </Stack>
      </CardContent>
    </Card>
  )
}

function MiniStat({ icon, value, label }: { icon: React.ReactNode; value: string; label: string }) {
  return (
    <Stack direction="row" spacing={.75} alignItems="center" sx={{ flex: 1, minWidth: 0, '& svg': { fontSize: 19, color: 'primary.main' } }}>
      <>{icon}</>
      <Typography variant="body2" fontWeight={800}>{value}</Typography>
      <Typography variant="caption" color="text.secondary" noWrap>{label}</Typography>
    </Stack>
  )
}

