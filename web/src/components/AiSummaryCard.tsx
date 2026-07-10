import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import { Alert, Box, Button, Card, CardContent, Chip, Divider, Skeleton, Stack, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { activitiesApi, type AIDataBasis } from '../api'
import { errorMessage, formatDateTime } from '../utils/format'
import { AIDataBasisPanel } from './AIDataBasisPanel'

export function AiSummaryCard({ activityId, fallback, provider, dataBasis }: { activityId: string; fallback?: string | null; provider?: string | null; dataBasis?: AIDataBasis | null }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['activity', activityId, 'summary'], queryFn: () => activitiesApi.summary(activityId), retry: false })
  const generate = useMutation({
    mutationFn: (force: boolean) => activitiesApi.generateSummary(activityId, force),
    onSuccess: (data) => client.setQueryData(['activity', activityId, 'summary'], data),
  })
  const summary = query.data?.summary ?? fallback
  const activeProvider = query.data?.provider ?? provider

  return (
    <Card sx={{ height: '100%', background: 'radial-gradient(circle at 100% 0, rgba(165,200,56,.18), transparent 32%), linear-gradient(145deg, #F3FAF5, #FFFFFF)' }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={2}>
          <Stack direction="row" spacing={1.25} alignItems="center">
            <Box sx={{ width: 40, height: 40, display: 'grid', placeItems: 'center', borderRadius: 3, bgcolor: 'primary.main', color: 'white' }}><AutoAwesomeRoundedIcon /></Box>
            <div><Typography variant="h3">Avento Insight</Typography><Typography variant="body2" color="text.secondary">Deine KI-Auswertung</Typography></div>
          </Stack>
          {activeProvider && <Chip size="small" label={activeProvider} variant="outlined" />}
        </Stack>
        <Divider sx={{ my: 2 }} />
        {query.isLoading && !fallback ? <Skeleton variant="rounded" height={130} /> : summary ? (
          <>
            <Typography sx={{ lineHeight: 1.75, whiteSpace: 'pre-wrap' }}>{summary}</Typography>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary">{query.data?.updated_at ? `Erstellt ${formatDateTime(query.data.updated_at)}` : 'Automatisch aus deinen Fahrtdaten erstellt'}</Typography>
              <Button size="small" startIcon={<RefreshRoundedIcon />} onClick={() => generate.mutate(true)} disabled={generate.isPending}>Neu erstellen</Button>
            </Stack>
            <Box sx={{ mt: 1.5 }}>
              <AIDataBasisPanel dataBasis={query.data?.data_basis ?? dataBasis} provider={activeProvider} title="Datengrundlage der Auswertung" />
            </Box>
          </>
        ) : (
          <Stack spacing={1.5}>
            <Typography color="text.secondary">Lass Leistung, Strecke und Wetter zu einer persönlichen Zusammenfassung verbinden.</Typography>
            <Button variant="contained" onClick={() => generate.mutate(false)} disabled={generate.isPending} startIcon={<AutoAwesomeRoundedIcon />}>
              {generate.isPending ? 'KI analysiert …' : 'Zusammenfassung erstellen'}
            </Button>
          </Stack>
        )}
        {(query.isError || generate.isError) && <Alert severity="warning" sx={{ mt: 2 }}>{errorMessage(query.error ?? generate.error)}</Alert>}
      </CardContent>
    </Card>
  )
}
