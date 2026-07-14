import { useEffect, useState } from 'react'
import AddPhotoAlternateRoundedIcon from '@mui/icons-material/AddPhotoAlternateRounded'
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded'
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded'
import PersonAddRoundedIcon from '@mui/icons-material/PersonAddRounded'
import LockResetRoundedIcon from '@mui/icons-material/LockResetRounded'
import PasswordRoundedIcon from '@mui/icons-material/PasswordRounded'
import SaveRoundedIcon from '@mui/icons-material/SaveRounded'
import { Alert, Autocomplete, Avatar, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControlLabel, Stack, Switch, TextField, Typography } from '@mui/material'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi, profileApi, type HeartRateZone } from '../api'
import { useAuth } from '../auth/AuthContext'
import { AvatarCropDialog } from '../components/AvatarCropDialog'
import { PageHeader } from '../components/PageHeader'
import { errorMessage, formatDateTime } from '../utils/format'
import { useUiMode } from '../UiModeProvider'

export function ProfilePage() {
  const { profile, setProfile, logout } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState(profile?.display_name ?? '')
  const [hrMax, setHrMax] = useState<number | ''>(profile?.hr_max ?? '')
  const [hrRest, setHrRest] = useState<number | ''>(profile?.hr_rest ?? '')
  const [zones, setZones] = useState<HeartRateZone[]>(profile?.hr_zones ?? [])
  const [trainingGoals, setTrainingGoals] = useState<string[]>(profile?.training_goals ?? [])
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  useEffect(() => { if (profile) { setName(profile.display_name); setHrMax(profile.hr_max ?? ''); setHrRest(profile.hr_rest ?? ''); setZones(profile.hr_zones); setTrainingGoals(profile.training_goals ?? []) } }, [profile])
  const save = useMutation({
    mutationFn: () => profileApi.update({ display_name: name.trim(), hr_max: hrMax === '' ? null : Number(hrMax), hr_rest: hrRest === '' ? null : Number(hrRest), hr_zones: zones, training_goals: trainingGoals }),
    onSuccess: setProfile,
  })
  const uploadAvatar = useMutation({
    mutationFn: profileApi.uploadAvatar,
    onSuccess: (updated) => { setProfile(updated); setAvatarFile(null); setAvatarError(null) },
  })
  const deleteAvatar = useMutation({ mutationFn: profileApi.deleteAvatar, onSuccess: setProfile })
  function chooseAvatar(file?: File) {
    setAvatarError(null)
    if (!file) return
    if (file.size > 10 * 1024 * 1024) {
      setAvatarError('Das Profilbild darf maximal 10 MB groß sein.')
      return
    }
    setAvatarFile(file)
  }
  async function signOut() { await logout(); navigate('/login', { replace: true }) }
  return <>
    <PageHeader eyebrow="DEIN KONTO" title="Profil & Trainingszonen" description="Passe persönliche Werte an, damit deine Analysen besser zu dir passen." />
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 1fr) 360px' }, gap: 2.5 }}>
      <Card><CardContent sx={{ p: 3 }}><Stack spacing={2.5}>
        <Typography variant="h3">Profilbild</Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2.5} alignItems={{ xs: 'flex-start', sm: 'center' }}>
          <Avatar src={profile?.avatar_data_url ?? undefined} alt={profile?.display_name ?? 'Profilbild'} sx={{ width: 112, height: 112, bgcolor: 'secondary.light', color: 'secondary.dark', fontSize: '2.2rem', fontWeight: 800, border: '4px solid', borderColor: 'background.paper', boxShadow: '0 8px 24px rgba(20,50,45,.12)' }}>
            {profile?.display_name?.charAt(0).toUpperCase()}
          </Avatar>
          <Stack spacing={1} alignItems="flex-start">
            <Typography variant="body2" color="text.secondary">Wähle ein Bild bis 10 MB und bestimme den quadratischen Ausschnitt selbst.</Typography>
            <Stack direction="row" gap={1} flexWrap="wrap">
              <Button component="label" variant="outlined" startIcon={<AddPhotoAlternateRoundedIcon />}>
                Bild auswählen
                <Box component="input" hidden type="file" accept="image/*,.heic,.heif" onChange={(event: React.ChangeEvent<HTMLInputElement>) => { chooseAvatar(event.target.files?.[0]); event.target.value = '' }} />
              </Button>
              {profile?.avatar_data_url && <Button color="error" startIcon={<DeleteOutlineRoundedIcon />} disabled={deleteAvatar.isPending} onClick={() => deleteAvatar.mutate()}>{deleteAvatar.isPending ? 'Wird entfernt …' : 'Bild entfernen'}</Button>}
            </Stack>
          </Stack>
        </Stack>
        {(avatarError || uploadAvatar.isError || deleteAvatar.isError) && <Alert severity="error">{avatarError ?? errorMessage(uploadAvatar.error ?? deleteAvatar.error)}</Alert>}
        <Divider />
        <Typography variant="h3">Persönliche Daten</Typography>
        <TextField label="Anzeigename" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
        <TextField label="E-Mail-Adresse" value={profile?.email ?? ''} disabled fullWidth helperText="Die E-Mail-Adresse kann derzeit nicht geändert werden." />
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField label="Maximale Herzfrequenz" type="number" value={hrMax} onChange={(event) => setHrMax(event.target.value ? Number(event.target.value) : '')} fullWidth /><TextField label="Ruheherzfrequenz" type="number" value={hrRest} onChange={(event) => setHrRest(event.target.value ? Number(event.target.value) : '')} fullWidth /></Stack>
        <Typography variant="h3" sx={{ pt: 1 }}>Trainingsziele</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: -1.5 }}>Avento Insight nutzt diese Ziele für persönlichere Vergleiche, Motivation und Trainingshinweise.</Typography>
        <Autocomplete
          multiple
          freeSolo
          options={['Grundlagenausdauer', 'Geschwindigkeit', 'Langstrecke', 'Trainingshäufigkeit', 'Klettern', 'Regeneration']}
          value={trainingGoals}
          onChange={(_, values) => setTrainingGoals(values.map((value) => value.trim()).filter(Boolean))}
          renderInput={(params) => <TextField {...params} label="Ziele auswählen oder eingeben" placeholder="Weiteres Ziel" helperText="Mit Enter kannst du ein eigenes Ziel hinzufügen." />}
        />
        <Typography variant="h3" sx={{ pt: 1 }}>Herzfrequenzzonen</Typography>
        {zones.map((zone, index) => <Box key={`${zone.name}-${index}`} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: '1.3fr 1fr 1fr 52px' }, gap: 1 }}><TextField label="Zone" value={zone.name} onChange={(event) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} /><TextField label="Von bpm" type="number" value={zone.min_bpm} onChange={(event) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, min_bpm: Number(event.target.value) } : item))} /><TextField label="Bis bpm" type="number" value={zone.max_bpm} onChange={(event) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, max_bpm: Number(event.target.value) } : item))} /><Box component="input" aria-label={`Farbe ${zone.name}`} type="color" value={zone.color} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setZones((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, color: event.target.value } : item))} sx={{ width: 48, height: 40, p: .5, border: '1px solid', borderColor: 'divider', borderRadius: 2, bgcolor: 'transparent' }} /></Box>)}
        {save.isError && <Alert severity="error">{errorMessage(save.error)}</Alert>}{save.isSuccess && <Alert severity="success">Profil gespeichert.</Alert>}
        <Button variant="contained" startIcon={<SaveRoundedIcon />} disabled={!name.trim() || save.isPending} onClick={() => save.mutate()} sx={{ alignSelf: 'flex-start' }}>{save.isPending ? 'Wird gespeichert …' : 'Änderungen speichern'}</Button>
      </Stack></CardContent></Card>
      <Stack spacing={2.5}>
        <ExperimentsCard />
        <Card><CardContent><Typography variant="h3">Konto</Typography><Typography color="text.secondary" sx={{ my: 2 }}>Du bist als {profile?.email} angemeldet.</Typography><Button color="error" variant="outlined" startIcon={<LogoutRoundedIcon />} onClick={() => void signOut()}>Abmelden</Button></CardContent></Card>
        <SecurityCard />
        <ChangePasswordCard />
        {profile?.is_admin && <><InviteCard /><AdminPasswordResetCard /></>}
        <Card><CardContent><Typography variant="h3">Datenschutz</Typography><Typography color="text.secondary" sx={{ mt: 1, lineHeight: 1.7 }}>Deine Fahrten werden zentral in deiner privaten Avento-Installation gespeichert. Andere Konten können deine Aktivitäten nicht sehen.</Typography></CardContent></Card>
      </Stack>
    </Box>
    <AvatarCropDialog open={Boolean(avatarFile)} file={avatarFile} busy={uploadAvatar.isPending} onClose={() => setAvatarFile(null)} onConfirm={(file) => uploadAvatar.mutate(file)} />
  </>
}

export function ExperimentsCard() {
  const { minimal, pending, error, setUiMode, clearError } = useUiMode()
  const [confirmOpen, setConfirmOpen] = useState(false)

  async function confirmActivation() {
    const changed = await setUiMode('minimal')
    if (changed) setConfirmOpen(false)
  }

  return (
    <>
      <Card component="section" aria-labelledby="experiments-title">
        <CardContent>
          <Typography variant="overline" color="text.secondary">Einstellungen</Typography>
          <Typography id="experiments-title" variant="h3">Experimente</Typography>
          <FormControlLabel
            label="Minimal UI (Beta)"
            labelPlacement="start"
            control={(
              <Switch
                checked={minimal}
                disabled={pending}
                inputProps={{ 'aria-describedby': 'minimal-ui-description' }}
                onChange={(_, checked) => {
                  clearError()
                  if (checked) setConfirmOpen(true)
                  else void setUiMode('classic')
                }}
              />
            )}
            sx={{ justifyContent: 'space-between', width: '100%', ml: 0, mt: 1.5, '& .MuiFormControlLabel-label': { fontWeight: 720 } }}
          />
          <Typography id="minimal-ui-description" variant="body2" color="text.secondary" sx={{ mt: 1, lineHeight: 1.7 }}>
            Ein experimenteller Entwurf einer ruhigeren, minimalistischeren und hochwertigeren Benutzeroberfläche. Diese Version befindet sich noch in der Entwicklung. Einzelne Bereiche können unvollständig sein oder sich verändern.
          </Typography>
          {Boolean(error) && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage(error)}</Alert>}
        </CardContent>
      </Card>
      <Dialog open={confirmOpen} onClose={pending ? undefined : () => setConfirmOpen(false)} fullWidth maxWidth="sm" aria-labelledby="minimal-ui-confirm-title">
        <DialogTitle id="minimal-ui-confirm-title">Minimal UI aktivieren?</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary" sx={{ lineHeight: 1.75 }}>
            Diese Oberfläche befindet sich in einer Beta-Phase. Einzelne Bereiche können unvollständig sein, Darstellungsfehler enthalten oder sich in zukünftigen Versionen deutlich verändern. Du kannst jederzeit zur klassischen Oberfläche zurückkehren.
          </Typography>
          {Boolean(error) && <Alert severity="error" sx={{ mt: 2 }}>{errorMessage(error)}</Alert>}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setConfirmOpen(false)} disabled={pending}>Abbrechen</Button>
          <Button variant="contained" onClick={() => void confirmActivation()} disabled={pending} autoFocus>{pending ? 'Wird aktiviert …' : 'Beta aktivieren'}</Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

function SecurityCard() {
  const [totpEnabled, setTotpEnabled] = useState(false)
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null)
  const [code, setCode] = useState('')
  const [name, setName] = useState('Mein Passkey')
  const [passkeys, setPasskeys] = useState<{ id: string; name: string; created_at: string }[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { void Promise.all([authApi.totpStatus(), authApi.passkeys()]).then(([status, keys]) => { setTotpEnabled(status.enabled); setPasskeys(keys) }).catch((e) => setError(errorMessage(e))) }, [])
  const setupTotp = async () => { try { setError(null); setSetup(await authApi.totpSetup()) } catch (e) { setError(errorMessage(e)) } }
  const enableTotp = async () => { try { setError(null); await authApi.totpEnable(code); setTotpEnabled(true); setSetup(null); setCode('') } catch (e) { setError(errorMessage(e)) } }
  const disableTotp = async () => { try { await authApi.totpDisable(); setTotpEnabled(false) } catch (e) { setError(errorMessage(e)) } }
  const registerPasskey = async () => {
    try {
      if (!window.PublicKeyCredential) throw new Error('Passkeys werden von diesem Browser nicht unterstützt.')
      const data = await authApi.passkeyRegistrationOptions()
      const options = data.options as PublicKeyCredentialCreationOptions
      const fromBase64 = (value: string) => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - value.length % 4) % 4)), (c) => c.charCodeAt(0)).buffer
      options.challenge = fromBase64(options.challenge as unknown as string); options.user.id = fromBase64(options.user.id as unknown as string)
      const credential = await navigator.credentials.create({ publicKey: options }); if (!credential) throw new Error('Kein Passkey erstellt.')
      const toBase64 = (value: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      const created = credential as PublicKeyCredential; const response = created.response as AuthenticatorAttestationResponse
      const saved = await authApi.registerPasskey({ id: created.id, rawId: toBase64(created.rawId), type: created.type, response: { clientDataJSON: toBase64(response.clientDataJSON), attestationObject: toBase64(response.attestationObject) } }, data.challenge_token, name.trim() || 'Passkey')
      setPasskeys((current) => [...current, { ...saved, created_at: new Date().toISOString() }])
    } catch (e) { setError(errorMessage(e)) }
  }
  return <Card><CardContent><Typography variant="h3">Anmeldesicherheit</Typography><Typography color="text.secondary" sx={{ my: 1.5 }}>Schütze dein Konto zusätzlich mit einem Authenticator-Code oder einem Passkey.</Typography><Stack spacing={1.5}>
    {error && <Alert severity="error">{error}</Alert>}
    <Typography variant="subtitle1">TOTP-Authenticator</Typography>
    {totpEnabled ? <Button color="error" variant="outlined" onClick={() => void disableTotp()}>TOTP deaktivieren</Button> : setup ? <><Typography variant="body2">Scanne den folgenden Link in deiner Authenticator-App oder kopiere das Geheimnis: <strong>{setup.secret}</strong></Typography><Button component="a" href={setup.otpauth_uri}>Authenticator öffnen</Button><TextField label="6-stelliger Code" value={code} inputMode="numeric" onChange={(e) => setCode(e.target.value)} /><Button variant="contained" disabled={!/^\d{6}$/.test(code)} onClick={() => void enableTotp()}>TOTP aktivieren</Button></> : <Button variant="outlined" onClick={() => void setupTotp()}>TOTP einrichten</Button>}
    <Divider /><Typography variant="subtitle1">Passkeys</Typography>{passkeys.map((key) => <Stack key={key.id} direction="row" justifyContent="space-between" alignItems="center"><Typography variant="body2">{key.name}</Typography><Button size="small" color="error" onClick={() => void authApi.deletePasskey(key.id).then(() => setPasskeys((current) => current.filter((item) => item.id !== key.id)))}>Löschen</Button></Stack>)}<TextField label="Name für neuen Passkey" value={name} onChange={(e) => setName(e.target.value)} /><Button variant="outlined" onClick={() => void registerPasskey()}>Passkey hinzufügen</Button>
  </Stack></CardContent></Card>
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
