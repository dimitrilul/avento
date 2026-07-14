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

export function createMinimalTheme() {
  const base = createAppTheme('dark')

  return createTheme(base, {
    palette: {
      mode: 'dark',
      primary: { main: '#65C8C1', light: '#9DE2DD', dark: '#359B95', contrastText: '#061E1D' },
      secondary: { main: '#B8D95B', light: '#D9EE98', dark: '#7F9F2E', contrastText: '#142000' },
      background: { default: '#090E0D', paper: '#111817' },
      text: { primary: '#F3F7F6', secondary: '#96A5A2' },
      divider: alpha('#D8E6E3', .1),
      error: { main: '#FFB4AB' },
      success: { main: '#87D39B' },
      warning: { main: '#EBC477' },
      chart: {
        teal: '#65C8C1',
        lime: '#B8D95B',
        amber: '#EBC477',
        coral: '#E89586',
        blue: '#82AEDA',
      },
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: 'Manrope Variable, system-ui, sans-serif',
      h1: { fontSize: 'clamp(2.35rem, 7vw, 4.8rem)', lineHeight: 1.02, fontWeight: 690, letterSpacing: '-.055em' },
      h2: { fontSize: 'clamp(1.8rem, 4vw, 3rem)', lineHeight: 1.08, fontWeight: 680, letterSpacing: '-.045em' },
      h3: { fontSize: 'clamp(1.25rem, 2vw, 1.6rem)', lineHeight: 1.2, fontWeight: 680, letterSpacing: '-.025em' },
      h4: { fontSize: '1.05rem', lineHeight: 1.35, fontWeight: 680 },
      body1: { lineHeight: 1.7 },
      body2: { lineHeight: 1.6 },
      button: { fontWeight: 680, textTransform: 'none' },
      overline: { fontSize: '.69rem', lineHeight: 1.5, fontWeight: 750, letterSpacing: '.1em' },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          ':root': {
            '--avento-minimal-surface-subtle': '#0D1413',
            '--avento-minimal-surface-raised': '#17201F',
            '--avento-minimal-content-width': '1280px',
            '--avento-motion-fast': '120ms',
            '--avento-motion-normal': '180ms',
            '--avento-motion-slow': '240ms',
          },
          body: {
            colorScheme: 'dark',
            backgroundImage: 'radial-gradient(circle at 72% -20%, rgba(101,200,193,.08), transparent 38%)',
            transition: 'background-color var(--avento-motion-normal) ease, color var(--avento-motion-normal) ease',
          },
          '@media (prefers-reduced-motion: reduce)': {
            '*, *::before, *::after': {
              animationDuration: '0.01ms !important',
              animationIterationCount: '1 !important',
              scrollBehavior: 'auto !important',
              transitionDuration: '0.01ms !important',
            },
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: {
            minHeight: 44,
            borderRadius: 10,
            '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: 3 },
          },
        },
      },
      MuiIconButton: {
        styleOverrides: { root: { '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: 3 } } },
      },
      MuiLink: {
        styleOverrides: { root: { '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: 3, borderRadius: 4 } } },
      },
      MuiTab: {
        styleOverrides: { root: { minHeight: 44, '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: -2 } } },
      },
      MuiToggleButton: {
        styleOverrides: { root: { minHeight: 40, '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: -2 } } },
      },
      MuiMenuItem: {
        styleOverrides: { root: { '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: -2 } } },
      },
      MuiCard: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            border: '1px solid rgba(216,230,227,.08)',
            boxShadow: '0 18px 50px rgba(0,0,0,.16)',
          },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            backgroundImage: 'none',
            border: '1px solid rgba(216,230,227,.1)',
            '@media (max-width: 420px)': { margin: 12, width: 'calc(100% - 24px)', maxHeight: 'calc(100% - 24px)' },
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: { root: { '&:focus-visible': { outline: '2px solid #65C8C1', outlineOffset: -2 } } },
      },
      MuiChip: { styleOverrides: { root: { fontWeight: 650 } } },
      MuiLinearProgress: { styleOverrides: { root: { backgroundColor: 'rgba(216,230,227,.08)' } } },
      MuiTooltip: { defaultProps: { arrow: true } },
    },
  })
}
