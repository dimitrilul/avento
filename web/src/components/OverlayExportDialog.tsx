import type { Activity, TrackPoint } from '../api'
import { ShareStudioDialog } from '../share/ShareStudioDialog'
import { OVERLAY_TEMPLATES } from '../share/templates'
import type { AchievementInfo } from '../share/types'

export const OVERLAY_PRESETS = OVERLAY_TEMPLATES

export function OverlayExportDialog({ open, onClose, activity, points, achievement }: { open: boolean; onClose: () => void; activity: Activity; points: TrackPoint[]; achievement?: AchievementInfo | null }) {
  return <ShareStudioDialog open={open} onClose={onClose} content={{ kind: 'activity', activity, points, achievement }} />
}
