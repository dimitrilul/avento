import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded'
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded'
import { IconButton, Tooltip } from '@mui/material'
import { useThemeMode } from '../ThemeModeProvider'

export function ThemeModeToggle() {
  const { mode, toggleMode } = useThemeMode()
  const dark = mode === 'dark'
  const label = dark ? 'Hellen Modus aktivieren' : 'Dunklen Modus aktivieren'

  return (
    <Tooltip title={label}>
      <IconButton aria-label={label} onClick={toggleMode} color="inherit">
        {dark ? <LightModeRoundedIcon /> : <DarkModeRoundedIcon />}
      </IconButton>
    </Tooltip>
  )
}
