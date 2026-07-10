import { alpha, createTheme } from '@mui/material/styles'

declare module '@mui/material/styles' {
  interface Palette {
    chart: { teal: string; lime: string; amber: string; coral: string; blue: string }
  }
  interface PaletteOptions {
    chart?: { teal: string; lime: string; amber: string; coral: string; blue: string }
  }
}

export const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: 'light',
    primary: { main: '#0E6562', light: '#5A9692', dark: '#083B3A', contrastText: '#FFFFFF' },
    secondary: { main: '#A5C838', light: '#D9EF83', dark: '#637C16' },
    background: { default: '#F5F7F3', paper: '#FFFFFF' },
    text: { primary: '#172322', secondary: '#61706E' },
    divider: alpha('#173C39', 0.1),
    error: { main: '#BA1A1A' },
    chart: {
      teal: '#0E6562',
      lime: '#A5C838',
      amber: '#E9A23B',
      coral: '#E26D5A',
      blue: '#4D82BC',
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
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { minHeight: 44, borderRadius: 14 } },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: `1px solid ${alpha('#173C39', 0.08)}`,
          boxShadow: '0 12px 36px rgba(20, 50, 45, 0.05)',
        },
      },
    },
    MuiTextField: { defaultProps: { size: 'small' } },
    MuiSelect: { defaultProps: { size: 'small' } },
    MuiChip: { styleOverrides: { root: { fontWeight: 650 } } },
    MuiTooltip: { defaultProps: { arrow: true } },
  },
})
