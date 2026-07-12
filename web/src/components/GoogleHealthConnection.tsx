import { useState } from 'react'
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded'
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import HealthAndSafetyRoundedIcon from '@mui/icons-material/HealthAndSafetyRounded'
import LinkRoundedIcon from '@mui/icons-material/LinkRounded'
import SyncRoundedIcon from '@mui/icons-material/SyncRounded'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  Typography,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { healthApi, healthQueryKeys, type HealthConnectionStatus } from '../api'
import { errorMessage, formatDateTime } from '../utils/format'

const scopeLabels: Record<string, string> = {
  activity_and_fitness: 'Aktivität und Fitness',
  health_metrics_and_measurements: 'Gesundheitsmesswerte',
  sleep: 'Schlaf',
}

function readableScope(scope: string) {
  const key = scope.split('.').at(-2) ?? scope.split('/').at(-1) ?? scope
  return scopeLabels[key.replace(/\.readonly$/, '')] ?? key.replaceAll('_', ' ')
}

function connectionLabel(status?: string) {
  if (status === 'connected') return 'Verbunden'
  if (status === 'reauthorization_required') return 'Erneute Freigabe nötig'
  if (status === 'revoked') return 'Zugriff widerrufen'
  if (status === 'error') return 'Verbindung gestört'
  return 'Nicht verbunden'
}

export interface GoogleHealthConnectionProps {
  onAuthorization?: (url: string) => void
}

export function validateGoogleAuthorizationUrl(value: string, mockMode = false) {
  let target: URL
  try {
    target = new URL(value, window.location.origin)
  } catch {
    throw new Error('Google hat eine ungültige Autorisierungsadresse geliefert.')
  }
  const noEmbeddedCredentials = !target.username && !target.password && !target.hash
  const officialGoogle = (
    noEmbeddedCredentials
    && target.protocol === 'https:'
    && target.origin === 'https://accounts.google.com'
    && target.pathname === '/o/oauth2/v2/auth'
  )
  const localHostname = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
  const targetIsLoopback = ['localhost', '127.0.0.1', '::1'].includes(target.hostname)
  const sameOriginMock = (
    mockMode
    && localHostname
    && noEmbeddedCredentials
    && targetIsLoopback
    && ['http:', 'https:'].includes(target.protocol)
    && target.pathname.endsWith('/health/oauth/callback')
  )
  if (!officialGoogle && !sameOriginMock) {
    throw new Error('Die Google-Autorisierungsadresse wurde aus Sicherheitsgründen abgelehnt.')
  }
  return target.href
}

export function GoogleHealthConnection({
  onAuthorization = (url) => window.location.assign(url),
}: GoogleHealthConnectionProps) {
  const queryClient = useQueryClient()
  const [confirmDisconnect, setConfirmDisconnect] = useState(false)
  const connection = useQuery({
    queryKey: healthQueryKeys.connection,
    queryFn: healthApi.connection,
  })
  const connect = useMutation({
    mutationFn: () => healthApi.startOAuth(connection.data?.status === 'reauthorization_required'),
    onSuccess: (result) => onAuthorization(validateGoogleAuthorizationUrl(result.authorization_url, result.mock_mode)),
  })
  const sync = useMutation({
    mutationFn: () => healthApi.sync(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: healthQueryKeys.all })
    },
  })
  const disconnect = useMutation({
    mutationFn: healthApi.disconnect,
    onSuccess: async () => {
      setConfirmDisconnect(false)
      await queryClient.invalidateQueries({ queryKey: healthQueryKeys.all })
    },
  })

  return (
    <>
      <Card component="section" aria-labelledby="google-health-connection-title">
        <CardContent sx={{ p: 2.5 }}>
          <Stack spacing={2}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
              <Box>
                <Typography id="google-health-connection-title" variant="h3">Google Health</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Schlaf, Aktivität und ausgewählte Messwerte sicher in Avento verwenden.
                </Typography>
              </Box>
              <HealthAndSafetyRoundedIcon color="primary" />
            </Stack>

            {connection.isLoading && (
              <Stack direction="row" alignItems="center" gap={1.5} role="status">
                <CircularProgress size={22} />
                <Typography variant="body2" color="text.secondary">Verbindung wird geprüft …</Typography>
              </Stack>
            )}
            {connection.isError && (
              <Alert severity="error" action={<Button color="inherit" onClick={() => void connection.refetch()}>Erneut prüfen</Button>}>
                {errorMessage(connection.error)}
              </Alert>
            )}
            {connection.data && <ConnectionBody connection={connection.data} />}
            {connection.data?.enabled === false && (
              <Alert severity="info">Google Health ist in dieser Avento-Installation noch nicht konfiguriert.</Alert>
            )}

            {(connect.isError || sync.isError || disconnect.isError) && (
              <Alert severity="error">{errorMessage(connect.error ?? sync.error ?? disconnect.error)}</Alert>
            )}
            {sync.data && (
              <Alert severity={sync.data.status === 'succeeded' ? 'success' : 'warning'}>
                Synchronisation {sync.data.status === 'succeeded' ? 'abgeschlossen' : 'teilweise abgeschlossen'}:
                {' '}{sync.data.stored_count} Datensätze übernommen, {sync.data.rejected_count} verworfen.
              </Alert>
            )}

            {connection.data?.connected ? (
              <Stack direction={{ xs: 'column', sm: 'row' }} gap={1}>
                <Button
                  variant="contained"
                  startIcon={<SyncRoundedIcon />}
                  disabled={sync.isPending}
                  onClick={() => sync.mutate()}
                >
                  {sync.isPending ? 'Synchronisiert …' : 'Jetzt synchronisieren'}
                </Button>
                <Button
                  color="error"
                  startIcon={<DeleteOutlineRoundedIcon />}
                  onClick={() => setConfirmDisconnect(true)}
                >
                  Verbindung trennen
                </Button>
              </Stack>
            ) : connection.data?.enabled !== false ? (
              <Button
                variant="contained"
                startIcon={<LinkRoundedIcon />}
                disabled={connect.isPending}
                onClick={() => connect.mutate()}
              >
                {connect.isPending ? 'Google wird geöffnet …' : 'Mit Google Health verbinden'}
              </Button>
            ) : null}

            <Divider />
            <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.6 }}>
              Avento fordert ausschließlich Lesezugriff an. OAuth-Tokens bleiben verschlüsselt auf dem
              Avento-Server und werden weder im Browser gespeichert noch in Auswertungen angezeigt. Du
              kannst die Verbindung und die importierten Google-Health-Daten jederzeit löschen.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Dialog open={confirmDisconnect} onClose={() => setConfirmDisconnect(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Google Health trennen?</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary">
            Der Zugriff wird widerrufen und die zugehörigen importierten Gesundheitsdaten werden aus
            Avento entfernt. Andere Avento-Daten bleiben bestehen.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDisconnect(false)}>Abbrechen</Button>
          <Button color="error" variant="contained" disabled={disconnect.isPending} onClick={() => disconnect.mutate()}>
            {disconnect.isPending ? 'Wird getrennt …' : 'Verbindung trennen'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

function ConnectionBody({ connection }: { connection: HealthConnectionStatus }) {
  return (
    <Stack spacing={1.25}>
      <Stack direction="row" alignItems="center" gap={1}>
        <CheckCircleRoundedIcon
          fontSize="small"
          color={connection.connected ? 'success' : connection.status === 'error' ? 'error' : 'disabled'}
        />
        <Typography fontWeight={750}>{connectionLabel(connection.status)}</Typography>
      </Stack>
      {connection.last_sync_at && (
        <Typography variant="body2" color="text.secondary">
          Zuletzt synchronisiert: {formatDateTime(connection.last_sync_at)}
        </Typography>
      )}
      {connection.granted_scopes.length > 0 && (
        <Box>
          <Typography variant="caption" color="text.secondary">Freigegebene Bereiche</Typography>
          <Typography variant="body2">
            {[...new Set(connection.granted_scopes.map(readableScope))].join(' · ')}
          </Typography>
        </Box>
      )}
      {connection.missing_scopes.length > 0 && connection.connected && (
        <Alert severity="warning">Für vollständige Auswertungen fehlen noch Berechtigungen.</Alert>
      )}
      {connection.last_error_code && (
        <Typography variant="caption" color="error.main">Fehlercode: {connection.last_error_code}</Typography>
      )}
    </Stack>
  )
}
