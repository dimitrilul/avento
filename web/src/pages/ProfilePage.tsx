import { useEffect, useState } from 'react'
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded'
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded'
import PersonAddRoundedIcon from '@mui/icons-material/PersonAddRounded'
import LockResetRoundedIcon from '@mui/icons-material/LockResetRounded'
import PasswordRoundedIcon from '@mui/icons-material/PasswordRounded'
import SaveRoundedIcon from '@mui/icons-material/SaveRounded'
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from '@mui/material'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi, profileApi, type HeartRateZone } from '../api'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PageHeader'
import { errorMessage, formatDateTime } from '../utils/format'

export function ProfilePage() {
  const { profile, setProfile, logout } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState(profile?.display_name ?? '')
  const [hrMax, setHrMax] = useState<number | ''>(profile?.hr_max ?? '')
  const [hrRest, setHrRest] = useState<number | ''>(profile?.hr_rest ?? '')
  const [zones, setZones] = useState<HeartRateZone[]>(profile?.hr_zones ?? [])
  useEffect(() => { if (profile) { setName(profile.display_name); setHrMax(profile.hr_max ?? ''); setHrRest(profile.hr_rest ?? ''); setZones(profile.hr_zones) } }, [profile])
  const save = useMutation({
    mutationFn: () => profileApi.update({ display_name: name.trim(), hr_max: hrMax === '' ? null : Number(hrMax), hr_rest: hrRest === '' ? null : Number(hrRest), hr_zones: zones }),
    onSuccess: setProfile,
  })
  async function signOut() { await logout(); navigate('/login', { replace: true }) }
  return <>
    <PageHeader eyebrow="DEIN KONTO" title="Profil & Trainingszonen" description="Passe persönliche Werte an, damit deine Analysen besser zu dir passen." />
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 1fr) 360px' }, gap: 2.5 }}>
      <Card><CardContent sx={{ p: 3 }}><Stack spacing={2.5}>
        <Typography variant="h3">Persönliche Daten</Typography>
        <TextField label="Anzeigename" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
        <TextField label="E-Mail-Adresse" value={profile?.email ?? ''} disabled fullWidth helperText="Die E-Mail-Adresse kann derzeit nicht geändert werden." />
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField label="Maximale Herzfrequenz" type="number" value={hrMax} onChange={(event) => setHrMax(event.target.value ? Number(event.target.value) : '')} fullWidth /><TextField label="Ruheherzfrequenz" type="number" value={hrRest} onChange={(event) => setHrRest(event.target.value ? Number(event.target.value) : '')} fullWidth /></Stack>
        <Typography variant="h3" sx={{ pt: 1 }}>Herzfrequenzzonen</Typography>
        {zones.map((zone, index) => <Box key={`${zone.name}-${index}`} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: '1.3fr 1fr 1fr 52px' }, gap: 1 }}><TextField label="Zone" value={zone.name} onChange={(event) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} /><TextField label="Von bpm" type="number" value={zone.min_bpm} onChange={(event) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, min_bpm: Number(event.target.value) } : item))} /><TextField label="Bis bpm" type="number" value={zone.max_bpm} onChange={(event) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, max_bpm: Number(event.target.value) } : item))} /><Box component="input" aria-label={`Farbe ${zone.name}`} type="color" value={zone.color} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, color: event.target.value } : item))} sx={{ width: 48, height: 40, p: .5, border: '1px solid', borderColor: 'divider', borderRadius: 2, bgcolor: 'transparent' }} /></Box>)}
        {save.isError && <Alert severity="error">{errorMessage(save.error)}</Alert>}{save.isSuccess && <Alert severity="success">Profil gespeichert.</Alert>}
        <Button variant="contained" startIcon={<SaveRoundedIcon />} disabled={!name.trim() || save.isPending} onClick={() => save.mutate()} sx={{ alignSelf: 'flex-start' }}>{save.isPending ? 'Wird gespeichert …' : 'Änderungen speichern'}</Button>
      </Stack></CardContent></Card>
      <Stack spacing={2.5}>
        <Card><CardContent><Typography variant="h3">Konto</Typography><Typography color="text.secondary" sx={{ my: 2 }}>Du bist als {profile?.email} angemeldet.</Typography><Button color="error" variant="outlined" startIcon={<LogoutRoundedIcon />} onClick={() => void signOut()}>Abmelden</Button></CardContent></Card>
        <ChangePasswordCard />
        {profile?.is_admin && <><InviteCard /><AdminPasswordResetCard /></>}
        <Card><CardContent><Typography variant="h3">Datenschutz</Typography><Typography color="text.secondary" sx={{ mt: 1, lineHeight: 1.7 }}>Deine Fahrten werden zentral in deiner privaten Avento-Installation gespeichert. Andere Konten können deine Aktivitäten nicht sehen.</Typography></CardContent></Card>
      </Stack>
    </Box>
  </>
}

function InviteCard() {
  const [email, setEmail] = useState('')
  const [copied, setCopied] = useState(false)
  const invite = useMutation({ mutationFn: () => authApi.createInvitation(email.trim() || undefined) })
  const registrationUrl = invite.data ? `${window.location.origin}/registrieren?einladung=${encodeURIComponent(invite.data.token)}` : ''
  async function copy() { await navigator.clipboard.writeText(registrationUrl); setCopied(true) }
  return <Card><CardContent><Typography variant="h3">Person einladen</Typography><Typography color="text.secondary" sx={{ my: 1.5 }}>Administratoren können einen einmaligen Registrierungslink erzeugen.</Typography><Stack spacing={1.5}><TextField label="E-Mail (optional)" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />{invite.data ? <><TextField label="Einladungslink" value={registrationUrl} slotProps={{ input: { readOnly: true } }} /><Button startIcon={<ContentCopyRoundedIcon />} onClick={() => void copy()}>{copied ? 'Kopiert' : 'Link kopieren'}</Button></> : <Button variant="outlined" startIcon={<PersonAddRoundedIcon />} onClick={() => invite.mutate()} disabled={invite.isPending}>{invite.isPending ? 'Wird erstellt …' : 'Einladung erstellen'}</Button>}{invite.isError && <Alert severity="warning">{errorMessage(invite.error)}</Alert>}</Stack></CardContent></Card>
}

function AdminPasswordResetCard() {
  const [email, setEmail] = useState('')
  const [copied, setCopied] = useState(false)
  const reset = useMutation({ mutationFn: () => authApi.createPasswordReset(email.trim()) })
  const resetUrl = reset.data ? `${window.location.origin}/passwort-zuruecksetzen?token=${encodeURIComponent(reset.data.token)}` : ''
  async function copy() { await navigator.clipboard.writeText(resetUrl); setCopied(true) }
  return (
    <Card><CardContent>
      <Typography variant="h3">Passwort-Reset</Typography>
      <Typography color="text.secondary" sx={{ my: 1.5 }}>Erzeuge als Administrator einen einmaligen Reset-Link. Der Token wird nur jetzt angezeigt.</Typography>
      <Stack spacing={1.5}>
        <TextField label="E-Mail-Adresse" type="email" required value={email} onChange={(event) => { setEmail(event.target.value); reset.reset(); setCopied(false) }} />
        {reset.data ? <>
          <TextField label="Reset-Link" value={resetUrl} slotProps={{ input: { readOnly: true } }} />
          <Typography variant="caption" color="text.secondary">Gültig bis {formatDateTime(reset.data.expires_at)}</Typography>
          <Button startIcon={<ContentCopyRoundedIcon />} onClick={() => void copy()}>{copied ? 'Kopiert' : 'Reset-Link kopieren'}</Button>
        </> : <Button variant="outlined" startIcon={<LockResetRoundedIcon />} onClick={() => reset.mutate()} disabled={!email.trim() || reset.isPending}>{reset.isPending ? 'Wird erstellt …' : 'Reset-Link erstellen'}</Button>}
        {reset.isError && <Alert severity="warning">{errorMessage(reset.error)}</Alert>}
      </Stack>
    </CardContent></Card>
  )
}

function ChangePasswordCard() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [validation, setValidation] = useState<string | null>(null)
  const change = useMutation({
    mutationFn: () => profileApi.changePassword(currentPassword, newPassword),
    onSuccess: async () => {
      try { await logout() } catch { /* Tokens wurden serverseitig bereits widerrufen. */ }
      navigate('/login', { replace: true, state: { passwordChanged: true } })
    },
  })
  function submit() {
    setValidation(null)
    if (!currentPassword) return setValidation('Bitte gib dein aktuelles Passwort ein.')
    if (newPassword.length < 10) return setValidation('Das neue Passwort muss mindestens 10 Zeichen lang sein.')
    if (newPassword !== confirmation) return setValidation('Die neuen Passwörter stimmen nicht überein.')
    if (currentPassword === newPassword) return setValidation('Das neue Passwort muss sich vom aktuellen unterscheiden.')
    change.mutate()
  }
  return (
    <Card><CardContent>
      <Typography variant="h3">Passwort ändern</Typography>
      <Typography color="text.secondary" sx={{ my: 1.5 }}>Nach der Änderung werden alle Sitzungen beendet.</Typography>
      <Stack spacing={1.5}>
        <TextField label="Aktuelles Passwort" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
        <TextField label="Neues Passwort" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        <TextField label="Neues Passwort wiederholen" type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        {(validation || change.isError) && <Alert severity="error">{validation ?? errorMessage(change.error)}</Alert>}
        <Button variant="outlined" startIcon={<PasswordRoundedIcon />} disabled={change.isPending} onClick={submit}>{change.isPending ? 'Wird geändert …' : 'Passwort ändern'}</Button>
      </Stack>
    </CardContent></Card>
  )
}
