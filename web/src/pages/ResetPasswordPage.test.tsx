import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ResetPasswordPage } from './ResetPasswordPage'

describe('ResetPasswordPage', () => {
  it('übernimmt den Token aus dem Link und setzt das Passwort über die API zurück', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/passwort-zuruecksetzen?token=einmal-token']}>
          <ResetPasswordPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByLabelText(/reset-token/i)).toHaveValue('einmal-token')
    const passwordFields = screen.getAllByLabelText(/neues passwort/i)
    await user.type(passwordFields[0], 'mein-neues-passwort')
    await user.type(passwordFields[1], 'mein-neues-passwort')
    await user.click(screen.getByRole('button', { name: /passwort ändern/i }))

    await waitFor(() => expect(screen.getByText('Passwort geändert')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/password-reset', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ token: 'einmal-token', new_password: 'mein-neues-passwort' }),
    }))
  })
})
