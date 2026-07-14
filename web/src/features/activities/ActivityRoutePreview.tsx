import LocationOffRoundedIcon from '@mui/icons-material/LocationOffRounded'
import { Box, Skeleton, Stack, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { activitiesApi, type TrackPoint } from '../../api'

export function routePreviewPath(points: TrackPoint[], width = 240, height = 88) {
  const coordinates = points.flatMap((point) => (
    typeof point.longitude === 'number' && typeof point.latitude === 'number'
      ? [[point.longitude, point.latitude] as [number, number]]
      : []
  ))
  if (coordinates.length < 2) return null
  const longitudes = coordinates.map(([longitude]) => longitude)
  const latitudes = coordinates.map(([, latitude]) => latitude)
  const minLongitude = Math.min(...longitudes)
  const maxLongitude = Math.max(...longitudes)
  const minLatitude = Math.min(...latitudes)
  const maxLatitude = Math.max(...latitudes)
  const padding = 7
  const scaleX = (width - padding * 2) / Math.max(maxLongitude - minLongitude, .000001)
  const scaleY = (height - padding * 2) / Math.max(maxLatitude - minLatitude, .000001)
  const scale = Math.min(scaleX, scaleY)
  const routeWidth = (maxLongitude - minLongitude) * scale
  const routeHeight = (maxLatitude - minLatitude) * scale
  const offsetX = (width - routeWidth) / 2
  const offsetY = (height - routeHeight) / 2
  return coordinates.map(([longitude, latitude], index) => {
    const x = offsetX + (longitude - minLongitude) * scale
    const y = height - offsetY - (latitude - minLatitude) * scale
    return `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

export function ActivityRoutePreview({ activityId }: { activityId: string }) {
  const track = useQuery({
    queryKey: ['activity', activityId, 'track'],
    queryFn: () => activitiesApi.track(activityId),
    staleTime: 5 * 60_000,
  })
  if (track.isLoading) return <Skeleton variant="rounded" height={88} />
  const path = routePreviewPath(track.data?.points ?? [])
  if (!path) {
    return (
      <Stack height={88} alignItems="center" justifyContent="center" color="text.secondary" spacing={.5}>
        <LocationOffRoundedIcon fontSize="small" />
        <Typography variant="caption">Ohne GPS</Typography>
      </Stack>
    )
  }
  return (
    <Box component="svg" viewBox="0 0 240 88" role="img" aria-label="Vorschau der gefahrenen Route" sx={{ display: 'block', width: '100%', height: 88 }}>
      <path d={path} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </Box>
  )
}
