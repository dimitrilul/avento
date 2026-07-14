import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OneTimeSecretDialog } from './McpAdminPage'

function SecretHarness() {
  const [visible, setVisible] = useState(true)
  return (
    <OneTimeSecretDialog
      secret={visible ? { title: 'MCP-Client angelegt', label: 'Client-Secret', value: 'super-geheim-und-einmalig', clientId: 'avento-client-1' } : null}
      onClose={() => setVisible(false)}
    />
  )
}

describe('OneTimeSecretDialog', () => {
  it('entfernt das Geheimnis nach dem Schließen und persistiert es nicht', async () => {
    const user = userEvent.setup()
    render(<SecretHarness />)

    expect(screen.getByDisplayValue('super-geheim-und-einmalig')).toBeInTheDocument()
    expect(localStorage.length).toBe(0)

    await user.click(screen.getByRole('button', { name: 'Ich habe es sicher gespeichert' }))

    expect(screen.queryByDisplayValue('super-geheim-und-einmalig')).not.toBeInTheDocument()
    expect(localStorage.length).toBe(0)
  })

  it('meldet eine Kopieraktion zugänglich, ohne das Geheimnis zu persistieren', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    render(<SecretHarness />)

    await user.click(screen.getByRole('button', { name: 'In die Zwischenablage kopieren' }))

    expect(writeText).toHaveBeenCalledWith('super-geheim-und-einmalig')
    expect(screen.getByRole('status')).toHaveTextContent('Das Geheimnis wurde in die Zwischenablage kopiert.')
    expect(localStorage.length).toBe(0)
  })
})
