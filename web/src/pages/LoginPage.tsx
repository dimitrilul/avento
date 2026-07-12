import { useState } from 'react'
import LockRoundedIcon from '@mui/icons-material/LockRounded'
import { Alert, Box, Button, Divider, Link, Stack, TextField, Typography } from '@mui/material'
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { authApi } from '../api'
import { errorMessage } from '../utils/format'

export function LoginPage() {
  const { login, refreshProfile } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [totpCode, setTotpCode] = useState('')
  const [challengeToken, setChallengeToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const passwordChanged = Boolean((location.state as { passwordChanged?: boolean } | null)?.passwordChanged)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      const result = challengeToken
        ? await authApi.login2fa(challengeToken, totpCode)
        : await login(email.trim(), password, totpCode || undefined)
      if ('requires_2fa' in result && result.requires_2fa) {
        setChallengeToken(result.challenge_token ?? null)
        return
      }
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/'
      navigate(destination, { replace: true })
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setPending(false)
    }
  }

  async function passkeyLogin() {
    setPending(true); setError(null)
    try {
      if (!window.PublicKeyCredential) throw new Error('Passkeys werden von diesem Browser nicht unterstützt.')
      const data = await authApi.passkeyOptions(email.trim())
      const options = data.options as PublicKeyCredentialRequestOptions
      const fromBase64 = (value: string) => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4)), (c) => c.charCodeAt(0)).buffer
      options.challenge = fromBase64(options.challenge as unknown as string)
      options.allowCredentials = options.allowCredentials?.map((item) => ({ ...item, id: fromBase64(item.id as unknown as string) }))
      const credential = await navigator.credentials.get({ publicKey: options })
      if (!credential) throw new Error('Keine Passkey-Anmeldung erhalten.')
      const toBase64 = (value: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      const assertion = credential as PublicKeyCredential
      const response = assertion.response as AuthenticatorAssertionResponse
      await authApi.passkeyLogin({ id: assertion.id, rawId: toBase64(assertion.rawId), type: assertion.type, response: { clientDataJSON: toBase64(response.clientDataJSON), authenticatorData: toBase64(response.authenticatorData), signature: toBase64(response.signature), userHandle: response.userHandle ? toBase64(response.userHandle) : null } }, data.challenge_token)
      await refreshProfile()
      navigate('/', { replace: true })
    } catch (caught) { setError(errorMessage(caught)) } finally { setPending(false) }
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
      {challengeToken && <TextField label="Authenticator-Code" inputMode="numeric" autoComplete="one-time-code" required value={totpCode} onChange={(event) => setTotpCode(event.target.value)} />}
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
        {pending ? 'Anmeldung läuft …' : challengeToken ? '2FA bestätigen' : 'Anmelden'}
      </Button>
      <Button type="button" variant="outlined" onClick={() => void passkeyLogin()} disabled={pending || !email.trim()}>
        Passkey verwenden
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
