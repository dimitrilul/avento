import { Box, Stack, Typography } from '@mui/material'

/** Renders the small, safe Markdown subset used by AI responses. */
export function MarkdownText({ content }: { content: string }) {
  return (
    <Stack spacing={.75}>
      {content.split(/\r?\n/).map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) return <Box key={index} sx={{ height: .35 }} />
        const isListItem = /^[-*]\s+/.test(trimmed) || /^\d+[.)]\s+/.test(trimmed)
        const text = trimmed.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, '')
        return (
          <Box key={index} component={isListItem ? 'li' : 'div'} sx={isListItem ? { ml: 2, pl: .5 } : undefined}>
            <Typography component="span" sx={{ lineHeight: 1.7 }}>{renderInlineMarkdown(text)}</Typography>
          </Box>
        )
      })}
    </Stack>
  )
}

function renderInlineMarkdown(value: string) {
  return value.split(/(\*\*[^*]+\*\*)/g).map((part, index) => (
    part.startsWith('**') && part.endsWith('**')
      ? <Box component="strong" key={index} sx={{ fontWeight: 800 }}>{part.slice(2, -2)}</Box>
      : <span key={index}>{part}</span>
  ))
}
