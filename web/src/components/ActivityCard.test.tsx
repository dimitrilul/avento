import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Activity } from '../api'
import { ActivityCard } from './ActivityCard'

const activity: Activity = {
  id: 'ride-1',
  title: 'Runde um den See',
  type: 'tour',
  notes: null,
  started_at: '2026-07-10T08:30:00Z',
  distance_m: 52_400,
  duration_s: 7_800,
  moving_time_s: 7_200,
  elevation_gain_m: 640,
  avg_speed_mps: 7.28,
  max_speed_mps: 15,
  avg_hr_bpm: 142,
  max_hr_bpm: 181,
  avg_power_w: 188,
  avg_cadence_rpm: 84,
}

describe('ActivityCard', () => {
  it('zeigt die wichtigsten Fahrtdaten', () => {
    render(<MemoryRouter><ActivityCard activity={activity} /></MemoryRouter>)
    expect(screen.getByText('Runde um den See')).toBeInTheDocument()
    expect(screen.getByText('Tour')).toBeInTheDocument()
    expect(screen.getByText('52,4 km')).toBeInTheDocument()
    expect(screen.getByText('640 m')).toBeInTheDocument()
  })
})
