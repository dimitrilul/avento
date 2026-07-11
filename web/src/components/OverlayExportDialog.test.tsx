import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Activity, TrackPoint } from '../api'
import { OVERLAY_PRESETS, OverlayExportDialog } from './OverlayExportDialog'

const activity: Activity = {
  id: 'ride-1',
  title: 'Feierabendrunde',
  type: 'ride',
  notes: null,
  started_at: '2026-07-10T17:30:00Z',
  distance_m: 42195,
  duration_s: 7400,
  moving_time_s: 7000,
  elevation_gain_m: 610,
  avg_speed_mps: 6.03,
  max_speed_mps: 14.1,
  avg_hr_bpm: 146,
  max_hr_bpm: 181,
  avg_power_w: 208,
  avg_cadence_rpm: 87,
  hydration_ml: 750,
}

const points: TrackPoint[] = [
  { time: '2026-07-10T17:30:00Z', latitude: 52.5, longitude: 13.3 },
  { time: '2026-07-10T18:00:00Z', latitude: 52.52, longitude: 13.35 },
  { time: '2026-07-10T18:30:00Z', latitude: 52.49, longitude: 13.4 },
]

describe('OverlayExportDialog', () => {
  it('bietet zehn Vorlagen mit unterschiedlichen Karten-, Puls- und Transparenzvarianten', () => {
    expect(OVERLAY_PRESETS).toHaveLength(10)
    expect(OVERLAY_PRESETS.some((preset) => preset.transparent)).toBe(true)
    expect(OVERLAY_PRESETS.some((preset) => preset.showRoute && preset.showPulse)).toBe(true)
    expect(OVERLAY_PRESETS.some((preset) => !preset.showRoute && !preset.showPulse)).toBe(true)
  })

  it('wechselt die Vorlage und lässt Inhalte individuell ausblenden', () => {
    render(<OverlayExportDialog open onClose={() => undefined} activity={activity} points={points} />)

    expect(screen.getAllByText('Feierabendrunde')).toHaveLength(1)
    fireEvent.click(screen.getByText('Glass'))
    expect(screen.getByText('Transparenter Hintergrund')).toBeInTheDocument()
    expect(screen.getByTestId('overlay-canvas')).toHaveStyle({ background: 'transparent' })
    expect(screen.getByTestId('overlay-canvas').querySelector('[style*="backdrop-filter"]')).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Titel'))
    expect(screen.queryByText('Feierabendrunde')).not.toBeInTheDocument()
  })
})
