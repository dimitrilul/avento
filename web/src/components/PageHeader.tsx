import { Box, Stack, Typography } from '@mui/material'

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'flex-end' }} gap={2.5} sx={{ mb: 3.5 }}>
      <Box>
        {eyebrow && <Typography variant="overline" color="primary.main" fontWeight={800} letterSpacing=".12em">{eyebrow}</Typography>}
        <Typography variant="h2" component="h1">{title}</Typography>
        {description && <Typography color="text.secondary" sx={{ mt: .75, maxWidth: 720 }}>{description}</Typography>}
      </Box>
      {action}
    </Stack>
  )
}
