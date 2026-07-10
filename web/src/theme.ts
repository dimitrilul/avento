import { alpha, createTheme, type PaletteMode } from '@mui/material/styles'

declare module '@mui/material/styles' {
  interface Palette {
    chart: { teal: string; lime: string; amber: string; coral: string; blue: string }
  }
  interface PaletteOptions {
    chart?: { teal: string; lime: string; amber: string; coral: string; blue: string }
  }
}

export function createAppTheme(mode: PaletteMode) {
  const dark = mode === 'dark'

  return createTheme({
    cssVariables: true,
    palette: {
      mode,
      primary: dark
        ? { main: '#65C8C1', light: '#94DED9', dark: '#32958F', contrastText: '#061E1D' }
        : { main: '#0E6562', light: '#5A9692', dark: '#083B3A', contrastText: '#FFFFFF' },
      secondary: dark
        ? { main: '#B8D95B', light: '#D7EC96', dark: '#7E9E29', contrastText: '#142000' }
        : { main: '#A5C838', light: '#D9EF83', dark: '#637C16' },
      background: dark
        ? { default: '#0D1413', paper: '#151E1D' }
        : { default: '#F5F7F3', paper: '#FFFFFF' },
      text: dark
        ? { primary: '#F0F5F3', secondary: '#A5B3B0' }
        : { primary: '#172322', secondary: '#61706E' },
      divider: alpha(dark ? '#D7E4E1' : '#173C39', dark ? 0.12 : 0.1),
      error: { main: dark ? '#FFB4AB' : '#BA1A1A' },
      success: { main: dark ? '#85D49A' : '#2E7D4A' },
      chart: {
        teal: dark ? '#65C8C1' : '#0E6562',
        lime: dark ? '#B8D95B' : '#A5C838',
        amber: dark ? '#F2B85B' : '#E9A23B',
        coral: dark ? '#F28C7B' : '#E26D5A',
        blue: dark ? '#7EAFE0' : '#4D82BC',
      },
    },
    shape: { borderRadius: 16 },
    typography: {
      fontFamily: 'Manrope Variable, system-ui, sans-serif',
      h1: { fontSize: 'clamp(2rem, 5vw, 3.5rem)', fontWeight: 750, letterSpacing: '-0.04em' },
      h2: { fontSize: 'clamp(1.65rem, 3vw, 2.25rem)', fontWeight: 750, letterSpacing: '-0.035em' },
      h3: { fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em' },
      h4: { fontSize: '1.1rem', fontWeight: 700 },
      button: { fontWeight: 700, textTransform: 'none' },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            colorScheme: mode,
            transition: 'background-color 180ms ease, color 180ms ease',
          },
          '@media (prefers-reduced-motion: reduce)': {
            body: { transition: 'none' },
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { minHeight: 44, borderRadius: 14 } },
      },
      MuiCard: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            border: `1px solid ${alpha(dark ? '#D7E4E1' : '#173C39', dark ? 0.1 : 0.08)}`,
            boxShadow: dark ? '0 16px 42px rgba(0, 0, 0, 0.2)' : '0 12px 36px rgba(20, 50, 45, 0.05)',
          },
        },
      },
      MuiTextField: { defaultProps: { size: 'small' } },
      MuiSelect: { defaultProps: { size: 'small' } },
      MuiChip: { styleOverrides: { root: { fontWeight: 650 } } },
      MuiTooltip: { defaultProps: { arrow: true } },
    },
  })
}
