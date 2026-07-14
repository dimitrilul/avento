import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import type { Activity, TrackPoint } from '../api'
import { OVERLAY_PRESETS, OverlayExportDialog } from './OverlayExportDialog'

const activity: Activity = {
  id: 'ride-1', title: 'Feierabendrunde', type: 'ride', notes: null,
  started_at: '2026-07-10T17:30:00Z', distance_m: 42195, duration_s: 7400,
  moving_time_s: 7000, elevation_gain_m: 610, avg_speed_mps: 6.03,
  max_speed_mps: 14.1, avg_hr_bpm: 146, max_hr_bpm: 181,
  avg_power_w: 208, avg_cadence_rpm: 87, hydration_ml: 750,
}

const points: TrackPoint[] = [
  { time: '2026-07-10T17:30:00Z', latitude: 52.5, longitude: 13.3 },
  { time: '2026-07-10T18:00:00Z', latitude: 52.52, longitude: 13.35 },
  { time: '2026-07-10T18:30:00Z', latitude: 52.49, longitude: 13.4 },
]

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><OverlayExportDialog open onClose={() => undefined} activity={activity} points={points} /></QueryClientProvider>)
}

describe('OverlayExportDialog', () => {
  it('bietet sechs eigenständige Vorlagen und vier Formate', () => {
    expect(OVERLAY_PRESETS.map((preset) => preset.id)).toEqual(['classic', 'minimal', 'photo', 'stats', 'map', 'achievement'])
    renderDialog()
    for (const format of ['1:1', '4:5', '9:16', '16:9']) expect(screen.getByRole('button', { name: format })).toBeInTheDocument()
  })

  it('wechselt Vorlage, Transparenz und sichtbare Inhalte', () => {
    renderDialog()
    expect(screen.getByText('Feierabendrunde')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Minimal/ }))
    expect(screen.getByRole('button', { name: 'Transparent' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByLabelText('Titel'))
    expect(screen.queryByText('Feierabendrunde')).not.toBeInTheDocument()
  })
})
