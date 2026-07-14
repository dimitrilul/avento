import ArrowDownwardRoundedIcon from '@mui/icons-material/ArrowDownwardRounded'
import ArrowUpwardRoundedIcon from '@mui/icons-material/ArrowUpwardRounded'
import CloudOffRoundedIcon from '@mui/icons-material/CloudOffRounded'
import InboxRoundedIcon from '@mui/icons-material/InboxRounded'
import {
  Alert,
  Box,
  Button,
  Chip,
  Skeleton,
  Stack,
  Typography,
  type SxProps,
  type Theme,
} from '@mui/material'

export function MinimalPageHeader({ eyebrow, title, description, action }: {
  eyebrow?: string
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <Stack component="header" direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'flex-end' }} gap={3} sx={{ maxWidth: action ? 'none' : 900, mb: { xs: 5, md: 7 }, pt: { md: 1 } }}>
      <Box minWidth={0}>
        {eyebrow && <Typography variant="overline" color="primary.main">{eyebrow}</Typography>}
        <Typography component="h1" variant="h1" sx={{ mt: eyebrow ? 1 : 0, overflowWrap: 'anywhere' }}>{title}</Typography>
        {description && <Typography color="text.secondary" sx={{ mt: 2, maxWidth: 760, fontSize: { xs: '1rem', md: '1.12rem' } }}>{description}</Typography>}
      </Box>
      {action && <Box sx={{ flex: 'none' }}>{action}</Box>}
    </Stack>
  )
}

export function MinimalSectionHeader({ id, eyebrow, title, description, action }: {
  id: string
  eyebrow?: string
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'flex-end' }} gap={2.5}>
      <Box minWidth={0}>
        {eyebrow && <Typography variant="overline" color="primary.main">{eyebrow}</Typography>}
        <Typography id={id} component="h2" variant="h2" sx={{ mt: eyebrow ? .75 : 0, overflowWrap: 'anywhere' }}>{title}</Typography>
        {description && <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 700 }}>{description}</Typography>}
      </Box>
      {action && <Box sx={{ flex: 'none' }}>{action}</Box>}
    </Stack>
  )
}

export function MinimalFilterBar({ children, ariaLabel = 'Filter' }: { children: React.ReactNode; ariaLabel?: string }) {
  return (
    <Box component="section" aria-label={ariaLabel} sx={{ p: { xs: 1.5, sm: 2 }, mb: 4, border: '1px solid', borderColor: 'divider', borderRadius: 3, bgcolor: 'var(--avento-minimal-surface-subtle)' }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ xs: 'stretch', sm: 'center' }} gap={1.25} flexWrap="wrap">{children}</Stack>
    </Box>
  )
}

export function MinimalMetric({ label, value, detail, delta, accent = 'primary.main', sx }: {
  label: string
  value: string
  detail?: string
  delta?: number | null
  accent?: string
  sx?: SxProps<Theme>
}) {
  return (
    <Box sx={[{ minWidth: 0, py: 2, borderTop: '1px solid', borderColor: 'divider' }, ...(sx ? (Array.isArray(sx) ? sx : [sx]) : [])]}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="h3" sx={{ mt: .75, color: accent, overflowWrap: 'anywhere' }}>{value}</Typography>
      {(detail || delta != null) && <Stack direction="row" alignItems="center" gap={1} flexWrap="wrap" sx={{ mt: 1 }}>
        {delta != null && <Chip size="small" icon={delta >= 0 ? <ArrowUpwardRoundedIcon /> : <ArrowDownwardRoundedIcon />} label={`${delta >= 0 ? '+' : '−'}${Math.abs(delta).toLocaleString('de-DE', { maximumFractionDigits: 1 })} %`} aria-label={`${delta >= 0 ? 'Anstieg' : 'Rückgang'} um ${Math.abs(delta).toLocaleString('de-DE', { maximumFractionDigits: 1 })} Prozent`} />}
        {detail && <Typography variant="caption" color="text.secondary">{detail}</Typography>}
      </Stack>}
    </Box>
  )
}

export function MinimalChartFrame({ id, title, description, summary, action, children, minHeight = 300 }: {
  id: string
  title: string
  description?: string
  summary: string
  action?: React.ReactNode
  children: React.ReactNode
  minHeight?: number
}) {
  return (
    <Box component="figure" aria-labelledby={`${id}-title`} aria-describedby={`${id}-summary`} sx={{ m: 0, minWidth: 0, p: { xs: 1.5, sm: 2.5 }, border: '1px solid', borderColor: 'divider', borderRadius: 3, bgcolor: 'var(--avento-minimal-surface-subtle)', overflow: 'visible' }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'flex-start' }} gap={1.5} sx={{ mb: 2 }}>
        <Box>
          <Typography id={`${id}-title`} component="figcaption" variant="h3">{title}</Typography>
          {description && <Typography variant="body2" color="text.secondary" sx={{ mt: .5 }}>{description}</Typography>}
        </Box>
        {action}
      </Stack>
      <Typography id={`${id}-summary`} className="avento-visually-hidden">{summary}</Typography>
      <Box sx={{ minWidth: 0, minHeight }}>{children}</Box>
    </Box>
  )
}

export function MinimalEmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <Stack alignItems="center" justifyContent="center" textAlign="center" spacing={1.5} sx={{ minHeight: 230, py: 6, px: 2 }}><InboxRoundedIcon sx={{ fontSize: 36, color: 'text.secondary' }} /><Typography component="h2" variant="h3">{title}</Typography><Typography color="text.secondary" sx={{ maxWidth: 480 }}>{description}</Typography>{action && <Box sx={{ pt: 1 }}>{action}</Box>}</Stack>
}

export function MinimalErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : 'Die Daten konnten nicht geladen werden.'
  return <Alert severity="error" icon={<CloudOffRoundedIcon />} action={onRetry ? <Button color="inherit" onClick={onRetry}>Erneut versuchen</Button> : undefined}>{message}</Alert>
}

export function MinimalPageSkeleton({ sections = 3 }: { sections?: number }) {
  return <Stack spacing={2} aria-label="Inhalte werden geladen">{Array.from({ length: sections }).map((_, index) => <Skeleton key={index} variant="rounded" height={index === 0 ? 150 : 280} />)}</Stack>
}
