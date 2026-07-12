import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material/styles'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import {
  healthApi,
  type HealthConnectionStatus,
  type HealthDataResponse,
  type HealthOverviewResponse,
} from '../api'
import { createAppTheme } from '../theme'
import { HealthPage } from './HealthPage'

const connection: HealthConnectionStatus = {
  connected: true,
  status: 'connected',
  granted_scopes: [
    'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly',
    'https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly',
    'https://www.googleapis.com/auth/googlehealth.sleep.readonly',
  ],
  missing_scopes: [],
  last_sync_at: '2026-07-12T06:30:00Z',
  last_error_code: null,
  data_sources: [{ platform: 'ANDROID', device_name: 'Pixel Watch', device_manufacturer: 'Google', application_name: 'Fitbit', last_seen_at: '2026-07-12T06:20:00Z' }],
}

const overview: HealthOverviewResponse = {
  date: '2026-07-12',
  generated_at: '2026-07-12T07:00:00Z',
  scores: {
    recovery: {
      value: 82,
      status: 'available',
      level: 'hoch',
      confidence: 'hoch',
      data_coverage: { percent: 95, missing_required_signals: [] },
      important_factors: [{ key: 'hrv', label: 'Herzfrequenzvariabilität', impact: 'positiv', contribution_points: 6.2 }],
    },
    energy: { value: 74, status: 'available', level: 'typisch', confidence: 'mittel', data_coverage: { percent: 84 } },
    training_load: { value: 58, raw_value: 67.5, raw_unit: 'Belastungspunkte', status: 'available', level: 'typisch', confidence: 'hoch' },
    resilience: { value: null, status: 'insufficient_baseline', level: null, confidence: 'keine' },
  },
  factors: [],
  coverage: { recovery_inputs: 0.95 },
  baselines: {},
  uncertainty: ['Für Resilienz fehlen noch ausreichend viele Vergleichstage.'],
}

const data: HealthDataResponse = {
  metrics: [
    { metric_type: 'steps', value: 9_420, unit: 'count', observed_at: null, start_at: null, end_at: null, local_date: '2026-07-12', imported_at: '2026-07-12T06:30:00Z' },
    { metric_type: 'active_calories', value: 520.5, unit: 'kcal', observed_at: null, start_at: null, end_at: null, local_date: '2026-07-12', imported_at: '2026-07-12T06:30:00Z' },
    { metric_type: 'total_calories', value: 2_140, unit: 'kcal', observed_at: null, start_at: null, end_at: null, local_date: '2026-07-12', imported_at: '2026-07-12T06:30:00Z' },
    { metric_type: 'resting_heart_rate', value: 56, unit: 'bpm', observed_at: null, start_at: null, end_at: null, local_date: '2026-07-12', imported_at: '2026-07-12T06:30:00Z' },
    { metric_type: 'hrv_rmssd', value: 62.4, unit: 'ms', observed_at: null, start_at: null, end_at: null, local_date: '2026-07-12', imported_at: '2026-07-12T06:30:00Z' },
  ],
  heart_rate: [],
  sleeps: [{
    id: 'sleep-1',
    start_at: '2026-07-11T21:30:00Z',
    end_at: '2026-07-12T05:30:00Z',
    local_date: '2026-07-12',
    sleep_type: 'STAGES',
    is_nap: false,
    minutes_asleep: 445,
    minutes_awake: 35,
    overlaps_other_session: false,
    stages: [
      { start_at: '2026-07-11T21:30:00Z', end_at: '2026-07-12T00:00:00Z', stage_type: 'LIGHT' },
      { start_at: '2026-07-12T00:00:00Z', end_at: '2026-07-12T01:30:00Z', stage_type: 'DEEP' },
      { start_at: '2026-07-12T01:30:00Z', end_at: '2026-07-12T03:00:00Z', stage_type: 'REM' },
    ],
  }],
  exercises: [{
    id: 'exercise-1',
    start_at: '2026-07-11T16:00:00Z',
    end_at: '2026-07-11T17:15:00Z',
    local_date: '2026-07-11',
    exercise_type: 'BIKING',
    title: 'Feierabendrunde',
    active_duration_seconds: 4_200,
    calories_kcal: 540,
    distance_m: 28_500,
    steps: null,
    average_heart_rate_bpm: 142,
    active_zone_minutes: 54,
    heart_rate_zone_seconds: { moderateTime: 1_800, vigorousTime: 1_200 },
  }],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <ThemeProvider theme={createAppTheme('light')}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><HealthPage /></MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}

describe('HealthPage', () => {
  it('zeigt einen klaren Ladezustand', () => {
    vi.spyOn(healthApi, 'connection').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Google Health wird geladen …')).toBeInTheDocument()
  })

  it('zeigt einen Verbindungsfehler mit Wiederholungsaktion', async () => {
    vi.spyOn(healthApi, 'connection').mockRejectedValue(new Error('Status nicht erreichbar'))
    renderPage()
    expect(await screen.findByText('Status nicht erreichbar')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Erneut versuchen' })).toBeInTheDocument()
  })

  it('zeigt ohne Verbindung einen verständlichen Leerzustand', async () => {
    vi.spyOn(healthApi, 'connection').mockResolvedValue({ ...connection, connected: false, status: 'disconnected', granted_scopes: [], missing_scopes: connection.granted_scopes })
    const overviewSpy = vi.spyOn(healthApi, 'overview')
    const dataSpy = vi.spyOn(healthApi, 'data')
    renderPage()

    expect(await screen.findByText('Google Health ist nicht verbunden')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Google Health verbinden' })).toHaveAttribute('href', '/profil')
    expect(overviewSpy).not.toHaveBeenCalled()
    expect(dataSpy).not.toHaveBeenCalled()
  })

  it('zeigt bei verbundener, aber leerer Quelle eine Synchronisationsaufforderung', async () => {
    vi.spyOn(healthApi, 'connection').mockResolvedValue(connection)
    vi.spyOn(healthApi, 'overview').mockResolvedValue({ ...overview, scores: {}, uncertainty: [] })
    vi.spyOn(healthApi, 'data').mockResolvedValue({ metrics: [], heart_rate: [], sleeps: [], exercises: [] })
    renderPage()

    expect(await screen.findByText('Noch keine Gesundheitsdaten')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Synchronisieren' }).length).toBeGreaterThan(0)
  })

  it('zeigt Teilzustände weiter und berechnet keine Scores im Client', async () => {
    vi.spyOn(healthApi, 'connection').mockResolvedValue(connection)
    vi.spyOn(healthApi, 'overview').mockResolvedValue(overview)
    vi.spyOn(healthApi, 'data').mockRejectedValue(new Error('Rohdaten nicht verfügbar'))
    renderPage()

    expect(await screen.findByText(/Ein Teil der Gesundheitsansicht ist gerade nicht verfügbar/)).toBeInTheDocument()
    expect(screen.getByText('82')).toBeInTheDocument()
    expect(screen.getByText('74')).toBeInTheDocument()
    expect(screen.getAllByText('Kein Score').length).toBeGreaterThan(0)
    expect(screen.getByText(/ausschließlich serverseitig und deterministisch berechnet/)).toBeInTheDocument()
  })

  it('zeigt Übersicht, Schlaf, Bewegung, Belastung, Trends, Quelle und Syncstatus', async () => {
    vi.spyOn(healthApi, 'connection').mockResolvedValue(connection)
    vi.spyOn(healthApi, 'overview').mockResolvedValue(overview)
    vi.spyOn(healthApi, 'data').mockResolvedValue(data)
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Tagesform und Energie' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Schlaf' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Bewegung' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Trainingsbelastung' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Langfristige Trends' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Datenquelle und Synchronisationsstatus' })).toBeInTheDocument()
    expect(screen.getAllByText('9.420 Schritte').length).toBeGreaterThan(0)
    expect(screen.getByText('Feierabendrunde')).toBeInTheDocument()
    expect(screen.getByText('Google Health API')).toBeInTheDocument()
    expect(screen.getByText('Google Pixel Watch')).toBeInTheDocument()
    expect(screen.getByText(/keine medizinische Diagnose/)).toBeInTheDocument()
  })

  it('stößt eine manuelle Synchronisation an', async () => {
    const user = userEvent.setup()
    vi.spyOn(healthApi, 'connection').mockResolvedValue(connection)
    vi.spyOn(healthApi, 'overview').mockResolvedValue(overview)
    vi.spyOn(healthApi, 'data').mockResolvedValue(data)
    const sync = vi.spyOn(healthApi, 'sync').mockResolvedValue({
      run_id: 'run-1', status: 'succeeded', range_start: '2026-06-12T00:00:00Z', range_end: '2026-07-12T00:00:00Z', fetched_count: 30, stored_count: 28, rejected_count: 2, error_code: null,
    })
    renderPage()
    await screen.findByRole('heading', { name: 'Tagesform und Energie' })

    await user.click(screen.getByRole('button', { name: 'Synchronisieren' }))
    await waitFor(() => expect(sync).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/28 Datensätze übernommen/)).toBeInTheDocument()
  })
})
