import CloudOffRoundedIcon from '@mui/icons-material/CloudOffRounded'
import InboxRoundedIcon from '@mui/icons-material/InboxRounded'
import { Alert, Box, Button, CircularProgress, Stack, Typography } from '@mui/material'

export function LoadingScreen({ label = 'Wird geladen …' }: { label?: string }) {
  return (
    <Box sx={{ minHeight: '70vh', display: 'grid', placeItems: 'center', p: 3 }}>
      <Stack alignItems="center" spacing={2}>
        <CircularProgress size={36} />
        <Typography color="text.secondary">{label}</Typography>
      </Stack>
    </Box>
  )
}

export function ContentLoading({ label = 'Daten werden geladen …' }: { label?: string }) {
  return (
    <Stack alignItems="center" justifyContent="center" spacing={1.5} sx={{ minHeight: 240, p: 3 }}>
      <CircularProgress size={30} />
      <Typography variant="body2" color="text.secondary">{label}</Typography>
    </Stack>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Die Daten konnten nicht geladen werden.'
  return (
    <Alert
      severity="error"
      icon={<CloudOffRoundedIcon />}
      action={onRetry ? <Button color="inherit" onClick={onRetry}>Erneut versuchen</Button> : undefined}
      sx={{ borderRadius: '12px' }}
    >
      {message}
    </Alert>
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <Stack alignItems="center" textAlign="center" spacing={1.5} sx={{ py: 8, px: 3 }}>
      <Box sx={{ width: 60, height: 60, display: 'grid', placeItems: 'center', borderRadius: '12px', bgcolor: 'action.hover', color: 'text.secondary' }}>
        <InboxRoundedIcon fontSize="large" />
      </Box>
      <Typography variant="h3">{title}</Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 460 }}>{description}</Typography>
      {action && <Box sx={{ pt: 1 }}>{action}</Box>}
    </Stack>
  )
}
