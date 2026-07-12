import { useEffect, useMemo, useState } from 'react'
import FlagRoundedIcon from '@mui/icons-material/FlagRounded'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import type { GamificationGoal, GamificationGoalInput, GamificationMetric, GamificationPeriod } from '../../api'
import { errorMessage } from '../../utils/format'
import {
  gamificationMetricOptions,
  gamificationPeriodOptions,
  inputUnit,
  metricLabel,
  periodLabel,
  toApiTarget,
  toDisplayTarget,
} from './gamificationFormat'

interface GoalDialogProps {
  open: boolean
  goal?: GamificationGoal | null
  pending: boolean
  error?: unknown
  onClose: () => void
  onSubmit: (input: GamificationGoalInput) => void
}

export function GoalDialog({ open, goal, pending, error, onClose, onSubmit }: GoalDialogProps) {
  const [title, setTitle] = useState('')
  const [metric, setMetric] = useState<GamificationMetric>('distance_m')
  const [target, setTarget] = useState('')
  const [period, setPeriod] = useState<GamificationPeriod>('month')
  const [deadline, setDeadline] = useState('')
  const [validation, setValidation] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setTitle(goal?.title ?? '')
    setMetric(goal?.metric ?? 'distance_m')
    setTarget(goal ? String(toDisplayTarget(goal.metric, goal.target_value)) : '')
    setPeriod(goal?.period ?? 'month')
    setDeadline(goal?.deadline?.slice(0, 10) ?? '')
    setValidation(null)
  }, [goal, open])

  const metricOptions = useMemo(() => {
    if (gamificationMetricOptions.some((option) => option.value === metric)) return gamificationMetricOptions
    return [...gamificationMetricOptions, { value: metric, label: metricLabel(metric), inputUnit: inputUnit(metric) }]
  }, [metric])
  const periodOptions = useMemo(() => {
    if (gamificationPeriodOptions.some((option) => option.value === period)) return gamificationPeriodOptions
    return [...gamificationPeriodOptions, { value: period, label: periodLabel(period) }]
  }, [period])

  function submit(event: React.FormEvent) {
    event.preventDefault()
    setValidation(null)
    const numericTarget = Number(target)
    if (!title.trim()) return setValidation('Bitte gib deinem Ziel einen Namen.')
    if (title.trim().length > 80) return setValidation('Der Name darf höchstens 80 Zeichen lang sein.')
    if (!Number.isFinite(numericTarget) || numericTarget <= 0) return setValidation('Der Zielwert muss größer als null sein.')
    onSubmit({
      title: title.trim(),
      metric,
      target_value: toApiTarget(metric, numericTarget),
      period,
      deadline: deadline || null,
    })
  }

  return (
    <Dialog open={open} onClose={pending ? undefined : onClose} fullWidth maxWidth="sm" transitionDuration={0}>
      <Box component="form" onSubmit={submit}>
        <DialogTitle sx={{ pb: 1 }}>
          <Stack direction="row" spacing={1.25} alignItems="center">
            <FlagRoundedIcon color="primary" />
            <Typography component="span" variant="h3">{goal ? 'Ziel bearbeiten' : 'Eigenes Ziel anlegen'}</Typography>
          </Stack>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
            Wähle etwas, das zu deinem Alltag passt. Du kannst dein Ziel jederzeit ändern oder löschen.
          </Typography>
          <Stack spacing={2}>
            <TextField
              autoFocus
              required
              fullWidth
              label="Name des Ziels"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              inputProps={{ maxLength: 80 }}
              helperText={`${title.length}/80 Zeichen`}
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                select
                fullWidth
                label="Messwert"
                value={metric}
                onChange={(event) => setMetric(event.target.value)}
              >
                {metricOptions.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
              </TextField>
              <TextField
                required
                fullWidth
                type="number"
                label={`Zielwert${inputUnit(metric) ? ` (${inputUnit(metric)})` : ''}`}
                value={target}
                onChange={(event) => setTarget(event.target.value)}
                inputProps={{ min: 0.1, step: metric === 'activity_count' || metric === 'places_visited' ? 1 : 0.1 }}
              />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                select
                fullWidth
                label="Zeitraum"
                value={period}
                onChange={(event) => setPeriod(event.target.value)}
              >
                {periodOptions.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
              </TextField>
              <TextField
                fullWidth
                type="date"
                label="Enddatum (optional)"
                value={deadline}
                onChange={(event) => setDeadline(event.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
            </Stack>
            {(validation || Boolean(error)) && <Alert severity="error">{validation ?? errorMessage(error)}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={onClose} disabled={pending}>Abbrechen</Button>
          <Button type="submit" variant="contained" disabled={pending}>
            {pending ? 'Wird gespeichert …' : goal ? 'Änderungen speichern' : 'Ziel anlegen'}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  )
}
