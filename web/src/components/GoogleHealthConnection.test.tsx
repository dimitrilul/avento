import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material/styles'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { healthApi, type HealthConnectionStatus } from '../api'
import { createAppTheme } from '../theme'
import { GoogleHealthConnection, validateGoogleAuthorizationUrl } from './GoogleHealthConnection'

const disconnected: HealthConnectionStatus = {
  connected: false,
  status: 'disconnected',
  granted_scopes: [],
  missing_scopes: ['https://www.googleapis.com/auth/googlehealth.sleep.readonly'],
  last_sync_at: null,
  last_error_code: null,
}

const connected: HealthConnectionStatus = {
  connected: true,
  status: 'connected',
  granted_scopes: ['https://www.googleapis.com/auth/googlehealth.sleep.readonly'],
  missing_scopes: [],
  last_sync_at: '2026-07-12T06:30:00Z',
  last_error_code: null,
}

function renderConnection(onAuthorization = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(
    <ThemeProvider theme={createAppTheme('light')}>
      <QueryClientProvider client={queryClient}>
        <GoogleHealthConnection onAuthorization={onAuthorization} />
      </QueryClientProvider>
    </ThemeProvider>,
  )
  return onAuthorization
}

describe('validateGoogleAuthorizationUrl', () => {
  it('erlaubt ausschließlich den offiziellen Google-Host', () => {
    const url = 'https://accounts.google.com/o/oauth2/v2/auth?client_id=avento'
    expect(validateGoogleAuthorizationUrl(url)).toBe(url)
  })

  it.each([
    'javascript:alert(document.domain)',
    'data:text/html,unsafe',
    'https://accounts.google.com.evil.example/oauth',
    'https://evil.example/oauth',
    '//evil.example/oauth',
  ])('weist unsichere Weiterleitung %s zurück', (url) => {
    expect(() => validateGoogleAuthorizationUrl(url)).toThrow(/Sicherheitsgründen|ungültige/)
  })

  it('erlaubt same-origin nur im expliziten lokalen Mockmodus', () => {
    const url = `${window.location.origin}/api/v1/health/oauth/callback?code=mock-code&state=state`
    expect(() => validateGoogleAuthorizationUrl(url, false)).toThrow(/Sicherheitsgründen/)
    expect(validateGoogleAuthorizationUrl(url, true)).toBe(url)
  })
})

describe('GoogleHealthConnection', () => {
  it('legt den Leseumfang offen und öffnet eine geprüfte Google-Autorisierung', async () => {
    const user = userEvent.setup()
    vi.spyOn(healthApi, 'connection').mockResolvedValue(disconnected)
    vi.spyOn(healthApi, 'startOAuth').mockResolvedValue({
      authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=avento',
      expires_at: '2026-07-12T07:10:00Z',
      mock_mode: false,
    })
    const authorize = renderConnection()

    await user.click(await screen.findByRole('button', { name: 'Mit Google Health verbinden' }))

    await waitFor(() => expect(authorize).toHaveBeenCalledWith('https://accounts.google.com/o/oauth2/v2/auth?client_id=avento'))
    expect(screen.getByText(/ausschließlich Lesezugriff/)).toBeInTheDocument()
    expect(screen.getByText(/weder im Browser gespeichert/)).toBeInTheDocument()
  })

  it.each(['javascript:alert(1)', 'https://evil.example/oauth'])('öffnet keine unsichere OAuth-URL %s', async (authorizationUrl) => {
    const user = userEvent.setup()
    vi.spyOn(healthApi, 'connection').mockResolvedValue(disconnected)
    vi.spyOn(healthApi, 'startOAuth').mockResolvedValue({
      authorization_url: authorizationUrl,
      expires_at: '2026-07-12T07:10:00Z',
      mock_mode: false,
    })
    const authorize = renderConnection()

    await user.click(await screen.findByRole('button', { name: 'Mit Google Health verbinden' }))

    expect(await screen.findByText(/Sicherheitsgründen abgelehnt/)).toBeInTheDocument()
    expect(authorize).not.toHaveBeenCalled()
  })

  it('synchronisiert eine bestehende Verbindung', async () => {
    const user = userEvent.setup()
    vi.spyOn(healthApi, 'connection').mockResolvedValue(connected)
    const sync = vi.spyOn(healthApi, 'sync').mockResolvedValue({
      run_id: 'run-1', status: 'succeeded', range_start: '2026-06-12T00:00:00Z', range_end: '2026-07-12T00:00:00Z', fetched_count: 25, stored_count: 24, rejected_count: 1, error_code: null,
    })
    renderConnection()

    await user.click(await screen.findByRole('button', { name: 'Jetzt synchronisieren' }))

    await waitFor(() => expect(sync).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/24 Datensätze übernommen/)).toBeInTheDocument()
  })

  it('trennt erst nach ausdrücklicher Bestätigung', async () => {
    const user = userEvent.setup()
    vi.spyOn(healthApi, 'connection').mockResolvedValue(connected)
    const disconnect = vi.spyOn(healthApi, 'disconnect').mockResolvedValue(undefined)
    renderConnection()

    await user.click(await screen.findByRole('button', { name: 'Verbindung trennen' }))
    const dialog = screen.getByRole('dialog', { name: 'Google Health trennen?' })
    expect(disconnect).not.toHaveBeenCalled()
    await user.click(within(dialog).getByRole('button', { name: 'Verbindung trennen' }))

    await waitFor(() => expect(disconnect).toHaveBeenCalledTimes(1))
  })
})
