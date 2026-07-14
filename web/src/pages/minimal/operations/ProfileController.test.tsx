import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ProfileControllerProvider, useProfileController } from './ProfileController'

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({
    profile: { id: 'user-1', display_name: 'Dimitri', hr_max: 190, hr_rest: 55, hr_zones: [], training_goals: ['Ausdauer'] },
    setProfile: vi.fn(),
  }),
}))

function Editor({ variant }: { variant: string }) {
  const { name, setName, newPassword, setNewPassword } = useProfileController()
  return <><label>{variant}<input aria-label={`Name ${variant}`} value={name} onChange={(event) => setName(event.target.value)} /></label><label>Passwort<input aria-label={`Passwort ${variant}`} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label></>
}

function Harness() {
  const [minimal, setMinimal] = useState(false)
  return <ProfileControllerProvider><button onClick={() => setMinimal((value) => !value)}>Variante wechseln</button>{minimal ? <Editor variant="Minimal" /> : <Editor variant="Classic" />}</ProfileControllerProvider>
}

describe('ProfileControllerProvider', () => {
  it('bewahrt lokale Entwürfe beim Wechsel der UI-Variante', async () => {
    const user = userEvent.setup()
    const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    render(<QueryClientProvider client={client}><Harness /></QueryClientProvider>)

    await user.clear(screen.getByRole('textbox', { name: 'Name Classic' }))
    await user.type(screen.getByRole('textbox', { name: 'Name Classic' }), 'Neuer Entwurf')
    await user.type(screen.getByRole('textbox', { name: 'Passwort Classic' }), 'noch-nicht-gespeichert')
    await user.click(screen.getByRole('button', { name: 'Variante wechseln' }))

    expect(screen.getByRole('textbox', { name: 'Name Minimal' })).toHaveValue('Neuer Entwurf')
    expect(screen.getByRole('textbox', { name: 'Passwort Minimal' })).toHaveValue('noch-nicht-gespeichert')
  })
})
