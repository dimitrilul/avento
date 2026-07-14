import { Box, Stack, Typography } from '@mui/material'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import type { TrackPoint } from '../api'
import type { AchievementInfo } from './types'

type GpsPoint = TrackPoint & { longitude: number; latitude: number }

function mercator(point: GpsPoint) {
  const latitude = Math.max(-85, Math.min(85, point.latitude))
  return {
    x: point.longitude,
    y: Math.log(Math.tan(Math.PI / 4 + latitude * Math.PI / 360)) * 180 / Math.PI,
  }
}

function sampled(points: GpsPoint[], maximum = 1200) {
  if (points.length <= maximum) return points
  const stride = Math.ceil(points.length / maximum)
  const result = points.filter((_, index) => index % stride === 0)
  if (result.at(-1) !== points.at(-1)) result.push(points.at(-1)!)
  return result
}

export function gpsPoints(points: TrackPoint[]): GpsPoint[] {
  return points.filter((point): point is GpsPoint =>
    typeof point.longitude === 'number' && Number.isFinite(point.longitude)
    && typeof point.latitude === 'number' && Number.isFinite(point.latitude))
}

export function hasRoute(points: TrackPoint[]) {
  return gpsPoints(points).length >= 2
}

function paths(points: TrackPoint[], width: number, height: number, achievement?: AchievementInfo | null) {
  const gps = sampled(gpsPoints(points))
  if (gps.length < 2) return null
  const projected = gps.map(mercator)
  const minX = Math.min(...projected.map((point) => point.x))
  const maxX = Math.max(...projected.map((point) => point.x))
  const minY = Math.min(...projected.map((point) => point.y))
  const maxY = Math.max(...projected.map((point) => point.y))
  const rangeX = Math.max(maxX - minX, .000001)
  const rangeY = Math.max(maxY - minY, .000001)
  const padding = Math.min(width, height) * .1
  const scale = Math.min((width - padding * 2) / rangeX, (height - padding * 2) / rangeY)
  const drawnWidth = rangeX * scale
  const drawnHeight = rangeY * scale
  const offsetX = (width - drawnWidth) / 2
  const offsetY = (height - drawnHeight) / 2
  const coords = projected.map((point) => ({
    x: offsetX + (point.x - minX) * scale,
    y: height - offsetY - (point.y - minY) * scale,
  }))
  const full = coords.map(({ x, y }) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  let segment = ''
  if (achievement?.segmentStartM != null && achievement.segmentEndM != null) {
    segment = coords.filter((_, index) => {
      const distance = gps[index]?.distance_m
      return typeof distance === 'number' && distance >= achievement.segmentStartM! && distance <= achievement.segmentEndM!
    }).map(({ x, y }) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  }
  return { coords, full, segment }
}

export function RouteArtwork({
  points,
  color,
  halo,
  accent,
  achievement,
  label = true,
}: {
  points: TrackPoint[]
  color: string
  halo: string
  accent: string
  achievement?: AchievementInfo | null
  label?: boolean
}) {
  const width = 700
  const height = 430
  const route = paths(points, width, height, achievement)
  if (!route) return (
    <Stack alignItems="center" justifyContent="center" sx={{ width: '100%', height: '100%', opacity: .55 }}>
      <RouteRoundedIcon sx={{ fontSize: 64 }} />
      {label && <Typography fontSize={16} fontWeight={700}>Indoor-Aktivität</Typography>}
    </Stack>
  )
  return (
    <Box component="svg" viewBox={`0 0 ${width} ${height}`} sx={{ width: '100%', height: '100%', overflow: 'visible' }}>
      <polyline points={route.full} fill="none" stroke={halo} strokeWidth="15" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={route.full} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" />
      {route.segment && <polyline points={route.segment} fill="none" stroke={accent} strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />}
      <circle cx={route.coords[0].x} cy={route.coords[0].y} r="12" fill={accent} stroke={halo} strokeWidth="5" />
      <circle cx={route.coords.at(-1)!.x} cy={route.coords.at(-1)!.y} r="10" fill={color} stroke={accent} strokeWidth="5" />
    </Box>
  )
}
