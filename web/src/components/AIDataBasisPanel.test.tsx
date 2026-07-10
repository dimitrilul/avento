import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { AIDataBasis } from '../api'
import { AIDataBasisPanel } from './AIDataBasisPanel'

const dataBasis: AIDataBasis = {
  schema_version: '1.0',
  generated_at: '2026-07-10T12:00:00Z',
  period: {
    started_at: '2026-04-01T00:00:00Z',
    ended_at: '2026-06-30T23:59:59Z',
    timezone: 'Europe/Berlin',
    label: 'Letztes Quartal',
  },
  activity_ids: ['ride-1'],
  metrics: [{ name: 'Durchschnittstempo', value: 27.4, unit: 'km/h', activity_id: 'ride-1', source: 'activities', method: 'median' }],
  methods: [{ name: 'robust_association', description: 'Robuster Vergleich ähnlicher Fahrten.', parameters: { minimum_sample: 8 } }],
  limitations: ['Streckenwahl kann den Vergleich beeinflussen.'],
  facts: { activity_count: 12 },
}

describe('AIDataBasisPanel', () => {
  it('zeigt Zeitraum, Aktivitäten, Fakten, Methoden und Einschränkungen', () => {
    render(
      <MemoryRouter>
        <AIDataBasisPanel
          dataBasis={dataBasis}
          sources={[{ activity_id: 'ride-1', title: 'Runde am See', started_at: '2026-06-20T08:00:00Z' }]}
          tools={['get_training_statistics']}
          toolLabels={{ get_training_statistics: 'Statistik ausgewertet' }}
          provider="openai"
          defaultExpanded
        />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Letztes Quartal').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Runde am See/ })).toHaveAttribute('href', '/aktivitaeten/ride-1')
    expect(screen.getByText('27,4 km/h')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('Statistik ausgewertet')).toBeInTheDocument()
    expect(screen.getByText('robust_association')).toBeInTheDocument()
    expect(screen.getByText(/Streckenwahl kann/)).toBeInTheDocument()
  })
})
