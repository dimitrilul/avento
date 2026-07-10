import { useState } from 'react'
import LockRoundedIcon from '@mui/icons-material/LockRounded'
import { Alert, Box, Button, Divider, Link, Stack, TextField, Typography } from '@mui/material'
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { errorMessage } from '../utils/format'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const passwordChanged = Boolean((location.state as { passwordChanged?: boolean } | null)?.passwordChanged)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await login(email.trim(), password)
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/'
      navigate(destination, { replace: true })
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setPending(false)
    }
  }

  return (
    <Stack component="form" onSubmit={submit} spacing={2.5}>
      <Box>
        <Typography variant="h2">Willkommen zurück</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>Melde dich an und mach dort weiter, wo deine letzte Tour endete.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      {passwordChanged && <Alert severity="success">Dein Passwort wurde geändert. Melde dich jetzt neu an.</Alert>}
      <TextField
        label="E-Mail-Adresse"
        type="email"
        autoComplete="email"
        autoFocus
        required
        fullWidth
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <TextField
        label="Passwort"
        type="password"
        autoComplete="current-password"
        required
        fullWidth
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      <Box sx={{ textAlign: 'right', mt: -1 }}>
        <Link component={RouterLink} to="/passwort-zuruecksetzen" variant="body2" fontWeight={700}>Passwort zurücksetzen</Link>
      </Box>
      <Button type="submit" variant="contained" size="large" startIcon={<LockRoundedIcon />} disabled={pending}>
        {pending ? 'Anmeldung läuft …' : 'Anmelden'}
      </Button>
      <Divider>oder</Divider>
      <Typography textAlign="center" color="text.secondary">
        Du hast eine Einladung?{' '}
        <Link component={RouterLink} to="/registrieren" fontWeight={750}>Konto erstellen</Link>
      </Typography>
      <Typography variant="caption" textAlign="center" color="text.secondary">
        Neue Installation? <Link component={RouterLink} to="/einrichten">Erstes Konto einrichten</Link>
      </Typography>
    </Stack>
  )
}
