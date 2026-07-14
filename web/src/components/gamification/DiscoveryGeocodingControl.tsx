import { useState } from 'react'
import { Alert, Box, Button, LinearProgress, Link, Stack, Typography } from '@mui/material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  gamificationApi,
  gamificationOverviewQueryKey,
  type GamificationDiscoveryBackfillResult,
  type GamificationGeocodingStatus,
} from '../../api'
import { errorMessage } from '../../utils/format'

interface BackfillProgress {
  processed: number
  total: number
  available: number
  failed: number
  remaining: number
  rateLimited: boolean
  retryAfterSeconds: number | null
}

export function DiscoveryGeocodingControl({ geocoding }: { geocoding: GamificationGeocodingStatus }) {
  const queryClient = useQueryClient()
  const [progress, setProgress] = useState<BackfillProgress | null>(null)
  const backfill = useMutation({
    mutationFn: async (retryFailed: boolean) => {
      let aggregate: BackfillProgress = {
        processed: 0,
        total: 0,
        available: 0,
        failed: 0,
        remaining: 0,
        rateLimited: false,
        retryAfterSeconds: null,
      }
      while (true) {
        const batch: GamificationDiscoveryBackfillResult = await gamificationApi.backfillDiscoveries(retryFailed)
        aggregate = {
          processed: aggregate.processed + batch.processed,
          total: retryFailed
            ? Math.max(aggregate.total, batch.total, aggregate.processed + batch.processed)
            : Math.max(aggregate.total, aggregate.processed + batch.remaining, batch.total),
          available: aggregate.available + batch.available,
          failed: batch.failed,
          remaining: batch.remaining,
          rateLimited: batch.rate_limited,
          retryAfterSeconds: batch.retry_after_seconds,
        }
        setProgress(aggregate)
        if (batch.remaining === 0 || batch.rate_limited || (retryFailed && batch.failed > 0) || batch.processed === 0) break
      }
      return aggregate
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: gamificationOverviewQueryKey }),
  })

  const attribution = geocoding.attribution_label && geocoding.attribution_url
    ? <Link href={geocoding.attribution_url} target="_blank" rel="noreferrer">{geocoding.attribution_label}</Link>
    : null

  if (geocoding.status === 'disabled') {
    return <Alert severity="info" sx={{ mt: 2 }}>Die Ortserkennung ist auf diesem Server nicht aktiviert.</Alert>
  }
  if (geocoding.status === 'misconfigured') {
    return (
      <Box sx={{ mt: 2 }}>
        <Alert severity="error">Die Ortserkennung ist unvollständig konfiguriert oder LocationIQ hat den Schlüssel abgelehnt. Bitte prüfe Provider, EU-Endpunkt und LocationIQ-Schlüssel.</Alert>
        {backfill.isError && <Alert severity="error" sx={{ mt: 1.5 }}>{errorMessage(backfill.error)}</Alert>}
        <Button sx={{ mt: 1.5 }} variant="outlined" disabled={backfill.isPending} onClick={() => { setProgress(null); backfill.reset(); backfill.mutate(true) }}>
          {backfill.isPending ? 'Konfiguration wird geprüft …' : 'Konfiguration erneut prüfen'}
        </Button>
      </Box>
    )
  }

  const percent = progress?.total ? Math.min(100, progress.processed / progress.total * 100) : 0
  const canRetry = !backfill.isPending && Boolean(progress?.failed)
  return (
    <Box sx={{ mt: 2 }}>
      {geocoding.status === 'rate_limited' && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>Das LocationIQ-Kontingent ist vorübergehend ausgeschöpft. Bereits erkannte Orte bleiben erhalten.</Alert>
      )}
      {backfill.isError && <Alert severity="error" sx={{ mb: 1.5 }}>{errorMessage(backfill.error)}</Alert>}
      {progress && progress.total > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <LinearProgress variant="determinate" value={percent} aria-label="Fortschritt der Ortserkennung" />
          <Typography variant="caption" color="text.secondary" sx={{ mt: .5, display: 'block' }}>
            {progress.processed} von {progress.total} Fahrten verarbeitet
            {progress.failed ? ` · ${progress.failed} fehlgeschlagen` : ''}
          </Typography>
        </Box>
      )}
      {progress && progress.total === 0 && progress.failed === 0 && !backfill.isPending && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Alle vorhandenen Fahrten sind bereits verarbeitet.</Typography>
      )}
      {progress?.rateLimited && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          Verarbeitung pausiert{progress.retryAfterSeconds ? `; erneut möglich in etwa ${progress.retryAfterSeconds} Sekunden.` : '.'}
        </Alert>
      )}
      <Stack direction={{ xs: 'column', sm: 'row' }} gap={1.5} alignItems={{ sm: 'center' }}>
        <Button
          variant="outlined"
          disabled={backfill.isPending || geocoding.status === 'rate_limited'}
          onClick={() => { setProgress(null); backfill.reset(); backfill.mutate(false) }}
        >
          {backfill.isPending ? 'Orte werden ermittelt …' : 'Orte aus bestehenden Fahrten ermitteln'}
        </Button>
        {canRetry && (
          <Button onClick={() => { backfill.reset(); backfill.mutate(true) }}>Fehlgeschlagene erneut versuchen</Button>
        )}
        {attribution && <Typography variant="caption" color="text.secondary">Ortsdaten: {attribution}</Typography>}
      </Stack>
    </Box>
  )
}
