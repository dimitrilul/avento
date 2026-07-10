import { useState } from 'react'
import LockResetRoundedIcon from '@mui/icons-material/LockResetRounded'
import { Alert, Box, Button, Link, Stack, TextField, Typography } from '@mui/material'
import { useMutation } from '@tanstack/react-query'
import { Link as RouterLink, useSearchParams } from 'react-router-dom'
import { authApi } from '../api'
import { errorMessage } from '../utils/format'

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const [token, setToken] = useState(params.get('token') ?? '')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [validation, setValidation] = useState<string | null>(null)
  const reset = useMutation({ mutationFn: () => authApi.resetPassword(token.trim(), password) })

  function submit(event: React.FormEvent) {
    event.preventDefault()
    setValidation(null)
    if (!token.trim()) return setValidation('Bitte gib einen gültigen Reset-Token ein.')
    if (password.length < 10) return setValidation('Das neue Passwort muss mindestens 10 Zeichen lang sein.')
    if (password !== confirm) return setValidation('Die Passwörter stimmen nicht überein.')
    reset.mutate()
  }

  if (reset.isSuccess) {
    return (
      <Stack spacing={2.5} alignItems="flex-start">
        <LockResetRoundedIcon color="primary" sx={{ fontSize: 52 }} />
        <Box>
          <Typography variant="h2">Passwort geändert</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>Deine bisherigen Sitzungen wurden beendet. Du kannst dich jetzt mit deinem neuen Passwort anmelden.</Typography>
        </Box>
        <Alert severity="success" sx={{ width: '100%' }}>Das neue Passwort ist aktiv.</Alert>
        <Button component={RouterLink} to="/login" variant="contained">Zur Anmeldung</Button>
      </Stack>
    )
  }

  return (
    <Stack component="form" onSubmit={submit} spacing={2.25}>
      <Box>
        <Typography variant="h2">Passwort zurücksetzen</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>Öffne den Link deines Administrators oder füge den erhaltenen Token hier ein.</Typography>
      </Box>
      {(validation || reset.isError) && <Alert severity="error">{validation ?? errorMessage(reset.error)}</Alert>}
      <TextField label="Reset-Token" required autoFocus fullWidth value={token} onChange={(event) => setToken(event.target.value)} />
      <TextField label="Neues Passwort" type="password" autoComplete="new-password" required fullWidth value={password} onChange={(event) => setPassword(event.target.value)} helperText="Mindestens 10 Zeichen" />
      <TextField label="Neues Passwort wiederholen" type="password" autoComplete="new-password" required fullWidth value={confirm} onChange={(event) => setConfirm(event.target.value)} />
      <Button type="submit" variant="contained" size="large" startIcon={<LockResetRoundedIcon />} disabled={reset.isPending}>{reset.isPending ? 'Wird geändert …' : 'Passwort ändern'}</Button>
      <Typography textAlign="center" color="text.secondary"><Link component={RouterLink} to="/login">Zurück zur Anmeldung</Link></Typography>
    </Stack>
  )
}
