import { forwardRef } from 'react'
import { Box } from '@mui/material'
import { contentDate, contentTitle, metricValues, weatherLabel } from './content'
import { paletteFor } from './design'
import { ShareMap } from './ShareMap'
import { templateById } from './templates'
import { FORMAT_SPECS, type OverlayConfig, type ShareContent } from './types'

export const OverlayCanvas = forwardRef<HTMLDivElement, {
  content: ShareContent
  config: OverlayConfig
  photoUrl?: string | null
}>(function OverlayCanvas({ content, config, photoUrl }, ref) {
  const format = FORMAT_SPECS[config.formatId]
  const palette = paletteFor(config.theme)
  const template = templateById(config.templateId)
  const activity = content.kind === 'activity' ? content : null
  const canMap = Boolean(activity && activity.points.length > 1)
  const background = config.background === 'photo' && !photoUrl ? 'solid' : config.background
  const solid = config.solidColor || palette.canvas

  return (
    <Box
      data-testid="overlay-canvas"
      ref={ref}
      sx={{
        width: format.width,
        height: format.height,
        position: 'relative',
        overflow: 'hidden',
        color: palette.text,
        bgcolor: background === 'transparent' ? 'transparent' : solid,
        backgroundImage: background === 'solid' ? `radial-gradient(circle at 88% 8%, ${palette.accent}2A, transparent 30%), linear-gradient(145deg, ${solid}, ${palette.canvas})` : undefined,
        fontFamily: 'Manrope Variable, system-ui, sans-serif',
      }}
    >
      {background === 'photo' && photoUrl && <Box component="img" src={photoUrl} alt="" sx={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: `center ${config.photoPosition}%` }} />}
      {background === 'map' && canMap && <ShareMap points={activity!.points} theme={config.theme} palette={palette} showRoute={config.showRoute} achievement={activity!.achievement} />}
      {background === 'map' && !canMap && <Box sx={{ position: 'absolute', inset: 0, background: `linear-gradient(145deg, ${palette.canvas}, ${palette.surfaceStrong})` }} />}
      <Box sx={{ position: 'absolute', inset: 0 }}>
        {template.render({
          content,
          config,
          palette,
          metrics: metricValues(content, config.metrics),
          title: contentTitle(content),
          date: contentDate(content),
          weather: weatherLabel(content),
          landscape: format.width > format.height,
        })}
      </Box>
    </Box>
  )
})
