import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { activitiesApi, statisticsApi } from '../../api'
import { rangeForStatisticsPreset, useComparisonViewModel, useDevelopmentViewModel, useStatisticsViewModel } from './useAnalyticsViewModels'

function Wrapper({ entry, children }: { entry: string; children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return <QueryClientProvider client={client}><MemoryRouter initialEntries={[entry]}>{children}</MemoryRouter></QueryClientProvider>
}

afterEach(() => vi.restoreAllMocks())

describe('analytics view models', () => {
  it('berechnet die Statistik-Presets deterministisch', () => {
    expect(rangeForStatisticsPreset('last_week', new Date('2026-07-14T12:00:00'))).toEqual({ from: '2026-07-06', to: '2026-07-12' })
    expect(rangeForStatisticsPreset('four_weeks', new Date('2026-07-14T12:00:00'))).toEqual({ from: '2026-06-17', to: '2026-07-14' })
  })

  it('liest Statistikfilter aus der URL und schreibt Änderungen zurück', async () => {
    vi.spyOn(statisticsApi, 'overview').mockResolvedValue({} as never)
    function Probe() {
      const vm = useStatisticsViewModel()
      const location = useLocation()
      return <><span>{`${vm.preset}|${vm.from}|${vm.to}|${vm.type}`}</span><span data-testid="url">{location.search}</span><button onClick={() => vm.update({ preset: 'year', type: 'tour' })}>ändern</button></>
    }
    render(<Wrapper entry="/statistiken?preset=custom&date_from=2026-01-02&date_to=2026-02-03&type=indoor"><Probe /></Wrapper>)
    expect(screen.getByText('custom|2026-01-02|2026-02-03|indoor')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'ändern' }))
    await waitFor(() => expect(screen.getByTestId('url').textContent).toContain('preset=year'))
    expect(screen.getByTestId('url').textContent).toContain('type=tour')
  })

  it('validiert Entwicklungsparameter und bewahrt gültigen URL-Zustand', () => {
    function Probe() { const vm = useDevelopmentViewModel(); return <span>{`${vm.years}|${vm.reviewYear}|${vm.season}`}</span> }
    render(<Wrapper entry="/entwicklung?years=5&review_year=2025&season=winter"><Probe /></Wrapper>)
    expect(screen.getByText('5|2025|winter')).toBeInTheDocument()
  })

  it('startet einen direkten Vergleich aus wiederholten activity-Parametern', async () => {
    vi.spyOn(activitiesApi, 'list').mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    const compare = vi.spyOn(activitiesApi, 'compare').mockResolvedValue({ activities: [], metrics: [], profiles: [], ai_summary: null, ai_provider: null, ai_data_basis: null })
    function Probe() { const vm = useComparisonViewModel(); return <span>{vm.selected.join(',')}</span> }
    render(<Wrapper entry="/vergleich?activity=a&activity=b&activity=c&activity=d&activity=e"><Probe /></Wrapper>)
    expect(screen.getByText('a,b,c,d')).toBeInTheDocument()
    await waitFor(() => expect(compare.mock.calls[0]?.[0]).toEqual(['a', 'b', 'c', 'd']))
  })
})
