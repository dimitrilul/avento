import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ThemeModeToggle } from './components/ThemeModeToggle'
import { ThemeModeProvider } from './ThemeModeProvider'

describe('ThemeModeProvider', () => {
  it('wechselt den Farbmodus und speichert die Auswahl', async () => {
    const user = userEvent.setup()
    render(
      <ThemeModeProvider>
        <ThemeModeToggle />
      </ThemeModeProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Dunklen Modus aktivieren' }))

    expect(screen.getByRole('button', { name: 'Hellen Modus aktivieren' })).toBeInTheDocument()
    expect(localStorage.getItem('avento-color-mode')).toBe('dark')
    expect(document.documentElement).toHaveAttribute('data-color-mode', 'dark')
  })
})
