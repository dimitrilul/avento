import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  it('meldet an und navigiert zur Übersicht', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'access', refresh_token: 'refresh', token_type: 'bearer', expires_in: 900 }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'user-1', email: 'rad@example.de', display_name: 'Radler', hr_max: null, hr_rest: null, hr_zones: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div>Übersicht geladen</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )
    await user.type(screen.getByRole('textbox', { name: /e-mail-adresse/i }), 'rad@example.de')
    await user.type(screen.getByLabelText(/passwort/i), 'sicheres-passwort')
    await user.click(screen.getByRole('button', { name: /anmelden/i }))
    await waitFor(() => expect(screen.getByText('Übersicht geladen')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
