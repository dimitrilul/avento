import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { CssBaseline, ThemeProvider } from '@mui/material'
import { profileApi, type UiMode } from './api'
import { tokenStore } from './api/client'
import { useAuth } from './auth/AuthContext'
import { createAppTheme, createMinimalTheme } from './theme'
import { useThemeMode } from './ThemeModeProvider'

interface UiModeContextValue {
  uiMode: UiMode
  minimal: boolean
  pending: boolean
  error: unknown
  setUiMode: (mode: UiMode) => Promise<boolean>
  clearError: () => void
}

const UiModeContext = createContext<UiModeContextValue | null>(null)
const uiModeHintKey = 'avento-ui-mode-hint'

function storedUiModeHint(): UiMode {
  if (!tokenStore.get()?.access_token) return 'classic'
  return localStorage.getItem(uiModeHintKey) === 'minimal' ? 'minimal' : 'classic'
}

export function UiModeProvider({ children }: { children: React.ReactNode }) {
  const { profile, setProfile } = useAuth()
  const { mode: colorMode } = useThemeMode()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [bootstrapMode, setBootstrapMode] = useState<UiMode>(storedUiModeHint)
  const uiMode: UiMode = profile ? (profile.ui_mode === 'minimal' ? 'minimal' : 'classic') : bootstrapMode
  const theme = useMemo(
    () => uiMode === 'minimal' ? createMinimalTheme() : createAppTheme(colorMode),
    [colorMode, uiMode],
  )

  useEffect(() => {
    document.documentElement.dataset.uiMode = uiMode
    return () => { delete document.documentElement.dataset.uiMode }
  }, [uiMode])

  useEffect(() => {
    if (profile) {
      const confirmed = profile.ui_mode === 'minimal' ? 'minimal' : 'classic'
      localStorage.setItem(uiModeHintKey, confirmed)
      setBootstrapMode(confirmed)
    } else if (!tokenStore.get()?.access_token) {
      localStorage.removeItem(uiModeHintKey)
      setBootstrapMode('classic')
    }
  }, [profile])

  const value = useMemo<UiModeContextValue>(() => ({
    uiMode,
    minimal: uiMode === 'minimal',
    pending,
    error,
    setUiMode: async (next) => {
      if (!profile || next === uiMode) return true
      setPending(true)
      setError(null)
      try {
        const updated = await profileApi.update({ ui_mode: next })
        localStorage.setItem(uiModeHintKey, updated.ui_mode)
        setBootstrapMode(updated.ui_mode)
        setProfile(updated)
        return true
      } catch (reason) {
        setError(reason)
        return false
      } finally {
        setPending(false)
      }
    },
    clearError: () => setError(null),
  }), [error, pending, profile, setProfile, uiMode])

  return (
    <UiModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </UiModeContext.Provider>
  )
}

export function useUiMode() {
  const context = useContext(UiModeContext)
  if (!context) throw new Error('useUiMode muss innerhalb des UiModeProvider verwendet werden.')
  return context
}
