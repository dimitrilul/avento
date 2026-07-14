import { Alert, Dialog, DialogContent, Skeleton } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { activitiesApi } from '../api'
import { errorMessage } from '../utils/format'
import { ShareStudioDialog } from './ShareStudioDialog'
import type { AchievementInfo } from './types'

export function AchievementShareDialog({ open, onClose, activityId, achievement }: { open: boolean; onClose: () => void; activityId: string | null; achievement: AchievementInfo | null }) {
  const activity = useQuery({ queryKey: ['activity', activityId], queryFn: () => activitiesApi.get(activityId!), enabled: open && Boolean(activityId) })
  const track = useQuery({ queryKey: ['activity', activityId, 'track'], queryFn: () => activitiesApi.track(activityId!), enabled: open && Boolean(activityId) })
  if (activity.data && achievement) return <ShareStudioDialog open={open} onClose={onClose} content={{ kind: 'activity', activity: activity.data, points: track.data?.points ?? [], achievement }} />
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm"><DialogContent>{activity.isError || track.isError ? <Alert severity="error">{errorMessage(activity.error ?? track.error)}</Alert> : <Skeleton variant="rounded" height={280} />}</DialogContent></Dialog>
}
