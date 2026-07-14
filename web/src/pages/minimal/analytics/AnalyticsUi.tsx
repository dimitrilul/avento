import ArrowDownwardRoundedIcon from '@mui/icons-material/ArrowDownwardRounded'
import ArrowUpwardRoundedIcon from '@mui/icons-material/ArrowUpwardRounded'
import RemoveRoundedIcon from '@mui/icons-material/RemoveRounded'
import { Box, Card, CardContent, Stack, Typography } from '@mui/material'

export function AnalyticsHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <Stack component="header" direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'flex-end' }} gap={3} sx={{ maxWidth: 1040, pt: { md: 2 } }}><Box><Typography variant="overline" color="primary.main">{eyebrow}</Typography><Typography component="h1" variant="h1" sx={{ mt: 1 }}>{title}</Typography><Typography color="text.secondary" sx={{ mt: 2, maxWidth: 720, fontSize: { xs: '1.05rem', md: '1.2rem' } }}>{description}</Typography></Box>{action}</Stack>
}

export function SectionHeading({ id, eyebrow, title, description }: { id: string; eyebrow?: string; title: string; description?: string }) {
  return <Box>{eyebrow && <Typography variant="overline" color="primary.main">{eyebrow}</Typography>}<Typography id={id} variant="h2" sx={{ mt: eyebrow ? 1 : 0 }}>{title}</Typography>{description && <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 700 }}>{description}</Typography>}</Box>
}

export function Metric({ label, value, change, hint }: { label: string; value: string; change?: number | null; hint?: string }) {
  const direction = change == null || change === 0 ? 'neutral' : change > 0 ? 'up' : 'down'
  const Icon = direction === 'up' ? ArrowUpwardRoundedIcon : direction === 'down' ? ArrowDownwardRoundedIcon : RemoveRoundedIcon
  return <Box sx={{ minWidth: 0, py: 1 }}><Typography variant="body2" color="text.secondary">{label}</Typography><Typography variant="h3" sx={{ mt: .75, overflowWrap: 'anywhere' }}>{value}</Typography>{change != null && <Stack direction="row" alignItems="center" gap={.5} sx={{ mt: 1 }}><Icon sx={{ fontSize: 17 }} aria-hidden="true" /><Typography variant="caption">{change > 0 ? '+' : ''}{change.toLocaleString('de-DE', { maximumFractionDigits: 1 })} % {hint}</Typography></Stack>}</Box>
}

export function ChartPanel({ title, description, summary, children }: { title: string; description: string; summary: string; children: React.ReactNode }) {
  return <Card component="section" sx={{ bgcolor: 'var(--avento-minimal-surface-subtle)', minWidth: 0, overflow: 'visible' }}><CardContent sx={{ p: { xs: 2.5, md: 4 }, '&:last-child': { pb: { xs: 2.5, md: 4 } } }}><Typography variant="h3">{title}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .75 }}>{description}</Typography><Box sx={{ mt: 3, mx: { xs: -1, sm: 0 }, minWidth: 0 }}>{children}</Box><Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>{summary}</Typography></CardContent></Card>
}

export const tooltipStyle = { background: '#161c1d', border: '1px solid rgba(255,255,255,.14)', borderRadius: 12, color: '#f4f7f6' }
