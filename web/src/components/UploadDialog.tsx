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
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [type, setType] = useState<ActivityType>('ride')
  const [dragActive, setDragActive] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: activitiesApi.import,
    onSuccess: async (activity) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['activities'] }),
        queryClient.invalidateQueries({ queryKey: ['statistics'] }),
      ])
      closeAndReset()
      navigate(`/aktivitaeten/${activity.id}`)
    },
  })

  function choose(next: File | undefined) {
    if (!next) return
    setFile(next)
    if (!title) setTitle(next.name.replace(/\.tcx$/i, '').replace(/[_-]+/g, ' '))
    mutation.reset()
  }

  function closeAndReset() {
    if (mutation.isPending) return
    setFile(null)
    setTitle('')
    setType('ride')
    mutation.reset()
    onClose()
  }

  return (
    <Dialog open={open} onClose={closeAndReset} fullWidth maxWidth="sm">
      {mutation.isPending && <LinearProgress />}
      <DialogTitle sx={{ pb: 1 }}>TCX-Aktivität importieren</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          <input
            ref={inputRef}
            hidden
            type="file"
            accept=".tcx,application/vnd.garmin.tcx+xml,application/xml,text/xml"
            onChange={(event) => choose(event.target.files?.[0])}
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
            {file ? (
              <Stack alignItems="center" spacing={1}>
                <InsertDriveFileRoundedIcon color="primary" fontSize="large" />
                <Typography fontWeight={750}>{file.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {(file.size / 1024 / 1024).toLocaleString('de-DE', { maximumFractionDigits: 1 })} MB · Klicken zum Ersetzen
                </Typography>
              </Stack>
            ) : (
              <Stack alignItems="center" spacing={1}>
                <CloudUploadRoundedIcon color="primary" fontSize="large" />
                <Typography fontWeight={750}>TCX-Datei hier ablegen</Typography>
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
            Die Datei wird verschlüsselt an deinen Avento-Server übertragen und dort analysiert.
          </Typography>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={closeAndReset} color="inherit">Abbrechen</Button>
        <Button
          variant="contained"
          startIcon={<CloudUploadRoundedIcon />}
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate({ file, title: title.trim() || undefined, type })}
        >
          {mutation.isPending ? 'Wird analysiert …' : 'Importieren'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
