import { useRef, useState } from 'react'
import CloudUploadRoundedIcon from '@mui/icons-material/CloudUploadRounded'
import InsertDriveFileRoundedIcon from '@mui/icons-material/InsertDriveFileRounded'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { activitiesApi, type ActivityType } from '../api'
import { activityTypes, errorMessage } from '../utils/format'

export function UploadDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [title, setTitle] = useState('')
  const [type, setType] = useState<ActivityType>('ride')
  const [dragActive, setDragActive] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (selected: File[]) => activitiesApi.importBatch(selected),
    onSuccess: async (batch) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['activities'] }),
        queryClient.invalidateQueries({ queryKey: ['statistics'] }),
      ])
      closeAndReset()
      const activityId = batch.jobs.length === 1 ? batch.jobs[0].activity_id : null
      if (activityId) navigate(`/aktivitaeten/${activityId}`)
    },
  })

  function choose(next: File | undefined) {
    if (!next) return
    setFiles([next])
    if (!title) setTitle(next.name.replace(/\.(tcx|fit|gpx)$/i, '').replace(/[_-]+/g, ' '))
    mutation.reset()
  }

  function closeAndReset() {
    if (mutation.isPending) return
    setFiles([])
    setTitle('')
    setType('ride')
    mutation.reset()
    onClose()
  }

  return (
    <Dialog open={open} onClose={closeAndReset} fullWidth maxWidth="sm">
      {mutation.isPending && <LinearProgress />}
          <DialogTitle sx={{ pb: 1 }}>Aktivitäten importieren</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <input
            ref={inputRef}
            hidden
            type="file"
            multiple
            accept=".tcx,.fit,.gpx,application/vnd.garmin.tcx+xml,application/octet-stream,application/gpx+xml,application/xml,text/xml"
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          />
          <Box
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(event) => event.key === 'Enter' && inputRef.current?.click()}
            onDragEnter={(event) => { event.preventDefault(); setDragActive(true) }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragActive(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragActive(false)
              choose(event.dataTransfer.files[0])
            }}
            sx={{
              border: '1.5px dashed',
              borderColor: dragActive ? 'primary.main' : 'divider',
              bgcolor: dragActive ? 'action.hover' : 'background.default',
              borderRadius: 4,
              p: 3.5,
              cursor: 'pointer',
              textAlign: 'center',
              transition: '150ms ease',
              '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
            }}
          >
            {files.length ? (
              <Stack alignItems="center" spacing={1}>
                <InsertDriveFileRoundedIcon color="primary" fontSize="large" />
                <Typography fontWeight={750}>{files.length === 1 ? files[0].name : `${files.length} Dateien ausgewählt`}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {files.length === 1 ? `${(files[0].size / 1024 / 1024).toLocaleString('de-DE', { maximumFractionDigits: 1 })} MB` : 'TCX, FIT und GPX werden unterstützt'} · Klicken zum Ersetzen
                </Typography>
              </Stack>
            ) : (
              <Stack alignItems="center" spacing={1}>
                <CloudUploadRoundedIcon color="primary" fontSize="large" />
                <Typography fontWeight={750}>TCX-, FIT- oder GPX-Dateien hier ablegen</Typography>
                <Typography variant="body2" color="text.secondary">oder vom Gerät auswählen</Typography>
              </Stack>
            )}
          </Box>
          <TextField
            label="Titel (optional)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            fullWidth
            disabled={mutation.isPending}
          />
          <FormControl fullWidth>
            <InputLabel id="upload-type-label">Aktivitätstyp</InputLabel>
            <Select
              labelId="upload-type-label"
              label="Aktivitätstyp"
              value={type}
              disabled={mutation.isPending}
              onChange={(event) => setType(event.target.value as ActivityType)}
            >
              {activityTypes.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}
            </Select>
          </FormControl>
          {mutation.isError && <Alert severity="error">{errorMessage(mutation.error)}</Alert>}
          <Typography variant="caption" color="text.secondary">
            Die Dateien werden übertragen und als idempotente Jobs verarbeitet. Fortschritt und Teilfehler bleiben pro Datei sichtbar.
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={closeAndReset} color="inherit">Abbrechen</Button>
        <Button
          variant="contained"
          startIcon={<CloudUploadRoundedIcon />}
          disabled={!files.length || mutation.isPending}
          onClick={() => files.length && mutation.mutate(files)}
        >
          {mutation.isPending ? 'Wird importiert …' : files.length > 1 ? `${files.length} Dateien importieren` : 'Importieren'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
