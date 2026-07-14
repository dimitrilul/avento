import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import { Button, Stack, Typography } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'

export function MinimalNotFoundPage() {
  return (
    <Stack component="section" alignItems="flex-start" spacing={2} sx={{ maxWidth: 680, py: { xs: 5, md: 10 } }}>
      <Typography variant="overline" color="primary.main">404 · Nicht gefunden</Typography>
      <Typography component="h1" variant="h1">Hier endet diese Strecke.</Typography>
      <Typography color="text.secondary" sx={{ fontSize: { md: '1.1rem' } }}>Die aufgerufene Seite existiert nicht oder wurde verschoben. Deine Aktivitäten und Einstellungen bleiben unverändert.</Typography>
      <Button component={RouterLink} to="/" variant="contained" startIcon={<ArrowBackRoundedIcon />}>Zur Übersicht</Button>
    </Stack>
  )
}
