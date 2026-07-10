import DirectionsBikeRoundedIcon from '@mui/icons-material/DirectionsBikeRounded'
import { Box, Typography } from '@mui/material'

export function Brand({ inverse = false, compact = false }: { inverse?: boolean; compact?: boolean }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, color: inverse ? 'white' : 'primary.dark' }}>
      <Box
        sx={{
          width: 40,
          height: 40,
          display: 'grid',
          placeItems: 'center',
          borderRadius: '13px',
          bgcolor: inverse ? 'rgba(255,255,255,.14)' : 'primary.main',
          color: 'white',
          transform: 'rotate(-3deg)',
        }}
      >
        <DirectionsBikeRoundedIcon />
      </Box>
      {!compact && (
        <Typography variant="h3" component="span" sx={{ fontWeight: 800, letterSpacing: '-.05em' }}>
          avento
        </Typography>
      )}
    </Box>
  )
}
