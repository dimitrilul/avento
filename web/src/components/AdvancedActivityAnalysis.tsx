import { useEffect, useMemo, useState } from 'react'
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded'
import FavoriteRoundedIcon from '@mui/icons-material/FavoriteRounded'
import LandscapeRoundedIcon from '@mui/icons-material/LandscapeRounded'
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded'
import RouteRoundedIcon from '@mui/icons-material/RouteRounded'
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded'
import SwapHorizRoundedIcon from '@mui/icons-material/SwapHorizRounded'
import TerrainRoundedIcon from '@mui/icons-material/TerrainRounded'
import ThermostatRoundedIcon from '@mui/icons-material/ThermostatRounded'
import ZoomOutMapRoundedIcon from '@mui/icons-material/ZoomOutMapRounded'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Slider,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  alpha,
  useTheme,
} from '@mui/material'
import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TrackPoint, WeatherData } from '../api'
import { formatDistance, formatElevation, formatHeartRate, formatSpeed } from '../utils/format'
import { EmptyState } from './States'
import { TrackMap } from './TrackMap'

type XAxisMode = 'distance' | 'time'
type SeriesKey = 'elevation' | 'speed' | 'heartRate'

type RouteWeatherPoint = {
  pointIndex: number
  distanceKm: number
  elapsedSeconds: number
  temperatureC: number
  apparentTemperatureC: number | null
}

export type AnalysisPoint = {
  index: number
  sourceIndex: number
  time: string
  distanceM: number
  distanceKm: number
  elapsedSeconds: number
  altitudeM: number | null
  speedKmh: number | null
  heartRateBpm: number | null
}

export type SectionMetrics = {
  distanceM: number
  durationSeconds: number
  averageSpeedKmh: number | null
  maximumSpeedKmh: number | null
  averageHeartRateBpm: number | null
  maximumHeartRateBpm: number | null
  elevationGainM: number
  elevationLossM: number
  averageGradientPercent: number | null
  maximumGradientPercent: number | null
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function coordinateDistance(first: TrackPoint, second: TrackPoint) {
  if (
    !isFiniteNumber(first.latitude) || !isFiniteNumber(first.longitude)
    || !isFiniteNumber(second.latitude) || !isFiniteNumber(second.longitude)
  ) return 0
  const toRadians = (degrees: number) => degrees * Math.PI / 180
  const earthRadiusM = 6_371_000
  const latitudeDelta = toRadians(second.latitude - first.latitude)
  const longitudeDelta = toRadians(second.longitude - first.longitude)
  const value = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(toRadians(first.latitude)) * Math.cos(toRadians(second.latitude))
      * Math.sin(longitudeDelta / 2) ** 2
  return earthRadiusM * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value))
}

export function buildAnalysisPoints(points: TrackPoint[]): AnalysisPoint[] {
  const firstTimestamp = points
    .map((point) => Date.parse(point.time))
    .find((timestamp) => Number.isFinite(timestamp))
  let cumulativeDistance = 0
  let rawDistanceOffset = 0
  let previousRawDistance: number | null = null
  let previousElapsed = 0

  return points.map((point, index) => {
    const rawDistance = isFiniteNumber(point.distance_m) ? Math.max(0, point.distance_m) : null
    if (rawDistance != null) {
      if (previousRawDistance != null && rawDistance < previousRawDistance) rawDistanceOffset = cumulativeDistance
      cumulativeDistance = Math.max(cumulativeDistance, rawDistanceOffset + rawDistance)
      previousRawDistance = rawDistance
    } else if (index > 0) {
      cumulativeDistance += coordinateDistance(points[index - 1], point)
    }

    const timestamp = Date.parse(point.time)
    const elapsedFromTimestamp = firstTimestamp != null && Number.isFinite(timestamp)
      ? Math.max(0, (timestamp - firstTimestamp) / 1000)
      : previousElapsed + (index ? 1 : 0)
    const elapsedSeconds = Math.max(previousElapsed, elapsedFromTimestamp)

    let speedKmh = isFiniteNumber(point.speed_mps) ? Math.max(0, point.speed_mps * 3.6) : null
    if (speedKmh == null && index > 0) {
      const previous = points[index - 1]
      const previousTimestamp = Date.parse(previous.time)
      const seconds = Number.isFinite(timestamp) && Number.isFinite(previousTimestamp)
        ? (timestamp - previousTimestamp) / 1000
        : 0
      const previousDistance = isFiniteNumber(previous.distance_m) ? previous.distance_m : null
      if (seconds > 0 && rawDistance != null && previousDistance != null && rawDistance >= previousDistance) {
        speedKmh = (rawDistance - previousDistance) / seconds * 3.6
      }
    }
    previousElapsed = elapsedSeconds

    return {
      index,
      sourceIndex: index,
      time: point.time,
      distanceM: cumulativeDistance,
      distanceKm: cumulativeDistance / 1000,
      elapsedSeconds,
      altitudeM: isFiniteNumber(point.altitude_m) ? point.altitude_m : null,
      speedKmh,
      heartRateBpm: isFiniteNumber(point.heart_rate_bpm) ? point.heart_rate_bpm : null,
    }
  })
}

function buildRouteWeatherPoints(
  weather: WeatherData | null | undefined,
  trackPoints: TrackPoint[],
  analysisPoints: AnalysisPoint[],
): RouteWeatherPoint[] {
  if (!Array.isArray(weather?.route_weather_samples)) return []
  return weather.route_weather_samples.flatMap((raw) => {
    if (!raw || typeof raw !== 'object') return []
    const sample = raw as Record<string, unknown>
    const pointIndex = isFiniteNumber(sample.point_index) ? Math.round(sample.point_index) : -1
    const temperatureC = sample.temperature_c
    if (pointIndex < 0 || pointIndex >= trackPoints.length || !isFiniteNumber(temperatureC)) return []
    const point = analysisPoints[pointIndex]
    if (!point) return []
    return [{
      pointIndex,
      distanceKm: point.distanceKm,
      elapsedSeconds: point.elapsedSeconds,
      temperatureC,
      apparentTemperatureC: isFiniteNumber(sample.apparent_temperature_c)
        ? sample.apparent_temperature_c
        : null,
    }]
  })
}

export function calculateSectionMetrics(
  points: AnalysisPoint[],
  startIndex: number,
  endIndex: number,
): SectionMetrics | null {
  if (!points.length) return null
  const start = Math.max(0, Math.min(startIndex, endIndex, points.length - 1))
  const end = Math.max(0, Math.min(Math.max(startIndex, endIndex), points.length - 1))
  const section = points.slice(start, end + 1)
  if (!section.length) return null

  const distanceM = Math.max(0, section.at(-1)!.distanceM - section[0].distanceM)
  const durationSeconds = Math.max(0, section.at(-1)!.elapsedSeconds - section[0].elapsedSeconds)
  const speeds = section.map((point) => point.speedKmh).filter(isFiniteNumber)
  const heartRates = section.map((point) => point.heartRateBpm).filter(isFiniteNumber)
  let elevationGainM = 0
  let elevationLossM = 0
  let maximumGradientPercent: number | null = null

  for (let index = 1; index < section.length; index += 1) {
    const previous = section[index - 1]
    const current = section[index]
    if (previous.altitudeM != null && current.altitudeM != null) {
      const difference = current.altitudeM - previous.altitudeM
      if (difference > 0) elevationGainM += difference
      else elevationLossM += Math.abs(difference)
      const segmentDistance = current.distanceM - previous.distanceM
      if (segmentDistance >= 10) {
        const gradient = difference / segmentDistance * 100
        maximumGradientPercent = maximumGradientPercent == null
          ? gradient
          : Math.max(maximumGradientPercent, gradient)
      }
    }
  }

  const firstAltitude = section.find((point) => point.altitudeM != null)?.altitudeM ?? null
  let lastAltitude: number | null = null
  for (let index = section.length - 1; index >= 0; index -= 1) {
    if (section[index].altitudeM != null) {
      lastAltitude = section[index].altitudeM
      break
    }
  }
  const averageGradientPercent = distanceM > 0 && firstAltitude != null && lastAltitude != null
    ? (lastAltitude - firstAltitude) / distanceM * 100
    : null

  return {
    distanceM,
    durationSeconds,
    averageSpeedKmh: durationSeconds > 0
      ? distanceM / durationSeconds * 3.6
      : speeds.length ? speeds.reduce((sum, value) => sum + value, 0) / speeds.length : null,
    maximumSpeedKmh: speeds.length ? Math.max(...speeds) : null,
    averageHeartRateBpm: heartRates.length
      ? heartRates.reduce((sum, value) => sum + value, 0) / heartRates.length
      : null,
    maximumHeartRateBpm: heartRates.length ? Math.max(...heartRates) : null,
    elevationGainM,
    elevationLossM,
    averageGradientPercent,
    maximumGradientPercent,
  }
}

function sampleForCharts(points: AnalysisPoint[], maximum = 1_800) {
  if (points.length <= maximum) return points
  const result: AnalysisPoint[] = []
  for (let index = 0; index < maximum; index += 1) {
    const sourceIndex = Math.round(index * (points.length - 1) / (maximum - 1))
    const point = points[sourceIndex]
    if (result.at(-1)?.index !== point.index) result.push(point)
  }
  return result
}

function formatElapsed(seconds: number, compact = false) {
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor(total % 3600 / 60)
  const remainder = total % 60
  if (compact) return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}`
    : `${minutes}:${String(remainder).padStart(2, '0')}`
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')} Std.`
    : `${minutes}:${String(remainder).padStart(2, '0')} Min.`
}

function formatAxisValue(value: number, mode: XAxisMode) {
  return mode === 'distance'
    ? `${Number(value).toLocaleString('de-DE', { maximumFractionDigits: 1 })} km`
    : formatElapsed(value, true)
}

function formatGradient(value: number | null) {
  return value == null
    ? '–'
    : `${value.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`
}

function formatSectionDistance(value: number) {
  if (value < 1_000) return `${Math.round(value).toLocaleString('de-DE')} m`
  return `${(value / 1000).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 2 })} km`
}

type AnalysisChartProps = {
  data: AnalysisPoint[]
  mode: XAxisMode
  series: SeriesKey
  color: string
  selection: [number, number] | null
  kilometerMarks: number[]
  activeIndex: number | null
  onHover: (index: number) => void
}

const chartDefinitions: Record<SeriesKey, {
  title: string
  dataKey: keyof AnalysisPoint
  unit: string
  emptyTitle: string
}> = {
  elevation: { title: 'Höhe', dataKey: 'altitudeM', unit: 'm', emptyTitle: 'Keine Höhendaten' },
  speed: { title: 'Geschwindigkeit', dataKey: 'speedKmh', unit: 'km/h', emptyTitle: 'Keine Geschwindigkeitsdaten' },
  heartRate: { title: 'Herzfrequenz', dataKey: 'heartRateBpm', unit: 'bpm', emptyTitle: 'Keine Herzfrequenzdaten' },
}

function AnalysisChart({ data, mode, series, color, selection, kilometerMarks, activeIndex, onHover }: AnalysisChartProps) {
  const theme = useTheme()
  const definition = chartDefinitions[series]
  const xKey: keyof AnalysisPoint = mode === 'distance' ? 'distanceKm' : 'elapsedSeconds'
  const hasValues = data.some((point) => point[definition.dataKey] != null)
  const selectionStart = selection ? (mode === 'distance' ? dataPoint(selection[0], data)?.distanceKm : dataPoint(selection[0], data)?.elapsedSeconds) : null
  const selectionEnd = selection ? (mode === 'distance' ? dataPoint(selection[1], data)?.distanceKm : dataPoint(selection[1], data)?.elapsedSeconds) : null
  const controlledIndex = activeIndex == null || !data.length
    ? undefined
    : data.reduce((nearestIndex, point, index) => (
      Math.abs(point.index - activeIndex) < Math.abs(data[nearestIndex].index - activeIndex) ? index : nearestIndex
    ), 0)

  if (!hasValues) {
    return (
      <Card>
        <CardContent sx={{ p: 2.5 }}>
          <Typography variant="h3">{definition.title}</Typography>
          <Stack justifyContent="center" sx={{ height: 180 }}>
            <EmptyState title={definition.emptyTitle} description="Für diese Aktivität wurden keine entsprechenden Messwerte aufgezeichnet." />
          </Stack>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent sx={{ p: { xs: 1.5, sm: 2.5 } }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color }} />
          <Typography variant="h3">{definition.title}</Typography>
          <Typography variant="body2" color="text.secondary">({definition.unit})</Typography>
        </Stack>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart
            data={data}
            syncId="advanced-activity-analysis"
            syncMethod="value"
            margin={{ top: 8, right: 14, left: -12, bottom: 4 }}
            onMouseMove={(state) => {
              const point = data[Number(state.activeTooltipIndex)]
              if (point) onHover(point.index)
            }}
          >
            <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={theme.palette.divider} />
            <XAxis
              dataKey={xKey}
              type="number"
              domain={['dataMin', 'dataMax']}
              tickCount={7}
              tickFormatter={(value) => formatAxisValue(Number(value), mode)}
              axisLine={false}
              tickLine={false}
              minTickGap={24}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              domain={series === 'speed' ? [0, 'auto'] : ['auto', 'auto']}
              unit={` ${definition.unit}`}
              width={62}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11 }}
            />
            {mode === 'distance' && kilometerMarks.map((kilometre) => (
              <ReferenceLine key={kilometre} x={kilometre} stroke={alpha(theme.palette.primary.main, .13)} />
            ))}
            {selectionStart != null && selectionEnd != null && (
              <ReferenceArea
                x1={Math.min(selectionStart, selectionEnd)}
                x2={Math.max(selectionStart, selectionEnd)}
                fill={theme.palette.chart.blue}
                fillOpacity={.1}
                stroke={theme.palette.chart.blue}
                strokeOpacity={.35}
              />
            )}
            <ChartTooltip active={controlledIndex == null ? undefined : true} defaultIndex={controlledIndex} content={({ active, payload }) => {
              const point = payload?.[0]?.payload as AnalysisPoint | undefined
              if (!active || !point) return null
              const value = point[definition.dataKey] as number | null
              return (
                <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2, boxShadow: 4, p: 1.25 }}>
                  <Typography variant="caption" color="text.secondary">{formatAxisValue(point[xKey] as number, mode)}</Typography>
                  <Typography variant="body2" fontWeight={750} sx={{ color }}>{value == null ? '–' : `${Math.round(value * 10) / 10} ${definition.unit}`}</Typography>
                </Box>
              )
            }} />
            {series === 'elevation' ? (
              <Area
                type="monotone"
                dataKey={definition.dataKey}
                stroke={color}
                strokeWidth={2}
                fill={alpha(color, .22)}
                connectNulls
                isAnimationActive={false}
              />
            ) : (
              <Line
                type="monotone"
                dataKey={definition.dataKey}
                stroke={color}
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

function WeatherRouteChart({ data, mode }: { data: RouteWeatherPoint[]; mode: XAxisMode }) {
  const theme = useTheme()
  const xKey: keyof RouteWeatherPoint = mode === 'distance' ? 'distanceKm' : 'elapsedSeconds'
  const temperatures = data.map((point) => point.temperatureC)
  const start = data[0].temperatureC
  const end = data.at(-1)!.temperatureC
  const minimum = Math.min(...temperatures)
  const maximum = Math.max(...temperatures)
  const change = end - start
  const formatTemperature = (value: number) => `${value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} °C`

  return (
    <Card>
      <CardContent sx={{ p: { xs: 1.5, sm: 2.5 } }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1.5} sx={{ mb: 1 }}>
          <Box>
            <Stack direction="row" alignItems="center" spacing={1}>
              <ThermostatRoundedIcon sx={{ color: 'chart.amber' }} />
              <Typography variant="h3">Temperaturverlauf</Typography>
              <Typography variant="body2" color="text.secondary">(°C)</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: .4 }}>
              Wetter zum jeweiligen Ort und Zeitpunkt entlang der Tour
            </Typography>
          </Box>
          <Stack direction="row" gap={.75} flexWrap="wrap">
            <Chip size="small" label={`Start ${formatTemperature(start)}`} />
            <Chip size="small" label={`Min. ${formatTemperature(minimum)}`} />
            <Chip size="small" label={`Max. ${formatTemperature(maximum)}`} />
            <Chip size="small" color={Math.abs(change) >= 3 ? 'warning' : 'default'} label={`Ende ${formatTemperature(end)} (${change >= 0 ? '+' : ''}${change.toLocaleString('de-DE', { maximumFractionDigits: 1 })}°)`} />
          </Stack>
        </Stack>
        <ResponsiveContainer width="100%" height={230}>
          <ComposedChart data={data} margin={{ top: 12, right: 18, left: -10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={theme.palette.divider} />
            <XAxis
              dataKey={xKey}
              type="number"
              domain={['dataMin', 'dataMax']}
              tickCount={7}
              tickFormatter={(value) => formatAxisValue(Number(value), mode)}
              axisLine={false}
              tickLine={false}
              minTickGap={24}
              tick={{ fontSize: 11 }}
            />
            <YAxis domain={['auto', 'auto']} unit=" °C" width={62} axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
            <ChartTooltip content={({ active, payload }) => {
              const point = payload?.[0]?.payload as RouteWeatherPoint | undefined
              if (!active || !point) return null
              return (
                <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 2, boxShadow: 4, p: 1.25 }}>
                  <Typography variant="caption" color="text.secondary">{formatAxisValue(point[xKey] as number, mode)}</Typography>
                  <Typography variant="body2" fontWeight={750} sx={{ color: 'chart.amber' }}>{formatTemperature(point.temperatureC)}</Typography>
                  {point.apparentTemperatureC != null && <Typography variant="caption" color="text.secondary">Gefühlt {formatTemperature(point.apparentTemperatureC)}</Typography>}
                </Box>
              )
            }} />
            <Area type="monotone" dataKey="temperatureC" stroke={theme.palette.chart.amber} strokeWidth={2.5} fill={alpha(theme.palette.chart.amber, .2)} dot={{ r: 4 }} activeDot={{ r: 6 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <Typography variant="caption" color="text.secondary">{data.length} Wetterstützpunkte; Werte zwischen den Punkten werden nur zur Orientierung verbunden.</Typography>
      </CardContent>
    </Card>
  )
}

function dataPoint(index: number, visiblePoints: AnalysisPoint[]) {
  if (!visiblePoints.length) return undefined
  if (index <= visiblePoints[0].index) return visiblePoints[0]
  if (index >= visiblePoints.at(-1)!.index) return visiblePoints.at(-1)
  return visiblePoints.reduce((nearest, point) => (
    Math.abs(point.index - index) < Math.abs(nearest.index - index) ? point : nearest
  ), visiblePoints[0])
}

function CurrentPointCard({ point }: { point: AnalysisPoint | null }) {
  const values = [
    ['Position', point ? formatDistance(point.distanceM) : '–'],
    ['Zeit', point ? formatElapsed(point.elapsedSeconds) : '–'],
    ['Höhe', formatElevation(point?.altitudeM)],
    ['Geschwindigkeit', formatSpeed(point?.speedKmh)],
    ['Herzfrequenz', formatHeartRate(point?.heartRateBpm)],
  ]
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ p: 2.5, height: '100%' }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.5 }}>
          <Box>
            <Typography variant="h3">Aktueller Punkt</Typography>
            <Typography variant="body2" color="text.secondary">Karte oder Diagramm berühren</Typography>
          </Box>
          <Chip size="small" color={point ? 'warning' : 'default'} label={point ? 'Synchronisiert' : 'Bereit'} />
        </Stack>
        <Stack divider={<Divider flexItem />}>
          {values.map(([label, value]) => (
            <Stack key={label} direction="row" justifyContent="space-between" spacing={2} sx={{ py: 1.15 }}>
              <Typography variant="body2" color="text.secondary">{label}</Typography>
              <Typography variant="body2" fontWeight={750} textAlign="right">{value}</Typography>
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  )
}

function SectionMetric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <Box sx={{ p: 1.75, borderRadius: 2.5, bgcolor: 'background.default', minWidth: 0 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ color: 'text.secondary', mb: .6 }}>
        {icon}
        <Typography variant="caption" fontWeight={700}>{label}</Typography>
      </Stack>
      <Typography variant="h4" noWrap title={value}>{value}</Typography>
    </Box>
  )
}

export function AdvancedActivityAnalysis({ points, weather }: { points: TrackPoint[]; weather?: WeatherData | null }) {
  const theme = useTheme()
  const analysisPoints = useMemo(() => buildAnalysisPoints(points), [points])
  const chartPoints = useMemo(() => sampleForCharts(analysisPoints), [analysisPoints])
  const routeWeather = useMemo(() => buildRouteWeatherPoints(weather, points, analysisPoints), [weather, points, analysisPoints])
  const [axisMode, setAxisMode] = useState<XAxisMode>('distance')
  const [visibleSeries, setVisibleSeries] = useState<SeriesKey[]>(['elevation', 'speed', 'heartRate'])
  const [zoomRange, setZoomRange] = useState<[number, number]>([0, Math.max(0, chartPoints.length - 1)])
  const [selection, setSelection] = useState<[number, number] | null>(null)
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  useEffect(() => {
    setZoomRange([0, Math.max(0, chartPoints.length - 1)])
    setSelection(null)
    setActiveIndex(null)
    setAxisMode(analysisPoints.at(-1)?.distanceM ? 'distance' : 'time')
  }, [analysisPoints, chartPoints])

  if (!analysisPoints.length) {
    return <EmptyState title="Keine Analysedaten" description="In dieser TCX-Datei sind keine Messpunkte enthalten." />
  }

  const safeZoomStart = Math.min(zoomRange[0], chartPoints.length - 1)
  const safeZoomEnd = Math.max(safeZoomStart, Math.min(zoomRange[1], chartPoints.length - 1))
  const visiblePoints = chartPoints.slice(safeZoomStart, safeZoomEnd + 1)
  const activePoint = activeIndex == null ? null : analysisPoints[activeIndex] ?? null
  const fullSelection: [number, number] = selection ?? [0, analysisPoints.length - 1]
  const selectionMetrics = selection
    ? calculateSectionMetrics(analysisPoints, selection[0], selection[1])
    : null
  const sectionSourceRange = selection ? {
    startIndex: analysisPoints[Math.min(selection[0], analysisPoints.length - 1)].sourceIndex,
    endIndex: analysisPoints[Math.min(selection[1], analysisPoints.length - 1)].sourceIndex,
  } : null
  const xKey: keyof AnalysisPoint = axisMode === 'distance' ? 'distanceKm' : 'elapsedSeconds'
  const lastKilometre = Math.floor(analysisPoints.at(-1)!.distanceKm)
  const kilometerMarks = Array.from({ length: lastKilometre }, (_, index) => index + 1)
  const seriesColors: Record<SeriesKey, string> = {
    elevation: theme.palette.chart.lime,
    speed: theme.palette.chart.blue,
    heartRate: theme.palette.chart.coral,
  }

  const useVisibleAreaAsSection = () => {
    const start = chartPoints[safeZoomStart]?.index ?? 0
    const end = chartPoints[safeZoomEnd]?.index ?? analysisPoints.length - 1
    setSelection([Math.min(start, end), Math.max(start, end)])
  }

  return (
    <Stack spacing={2.5}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 2.2fr) minmax(260px, .8fr)' }, gap: 2.5 }}>
        <Card sx={{ overflow: 'hidden' }}>
          <TrackMap
            points={points}
            activePointIndex={activePoint?.sourceIndex}
            selectedRange={sectionSourceRange}
            showKilometerMarkers
            onPointHover={setActiveIndex}
            height={{ xs: 390, md: 520 }}
          />
        </Card>
        <CurrentPointCard point={activePoint} />
      </Box>

      <Card>
        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', md: 'center' }} gap={2}>
            <Box>
              <Typography variant="h3">Diagrammansicht</Typography>
              <Typography variant="body2" color="text.secondary">Alle Kurven, Karte und Werte folgen demselben Messpunkt.</Typography>
            </Box>
            <Stack direction={{ xs: 'column', sm: 'row' }} gap={1.25}>
              <ToggleButtonGroup
                exclusive
                size="small"
                value={axisMode}
                onChange={(_, next: XAxisMode | null) => { if (next) setAxisMode(next) }}
                aria-label="X-Achse"
                fullWidth
              >
                <ToggleButton value="distance"><RouteRoundedIcon fontSize="small" sx={{ mr: .75 }} />Distanz</ToggleButton>
                <ToggleButton value="time"><AccessTimeRoundedIcon fontSize="small" sx={{ mr: .75 }} />Zeit</ToggleButton>
              </ToggleButtonGroup>
              <ToggleButtonGroup
                size="small"
                value={visibleSeries}
                onChange={(_, next: SeriesKey[]) => { if (next.length) setVisibleSeries(next) }}
                aria-label="Messreihen"
                fullWidth
              >
                <ToggleButton value="elevation">Höhe</ToggleButton>
                <ToggleButton value="speed">Tempo</ToggleButton>
                <ToggleButton value="heartRate">Puls</ToggleButton>
              </ToggleButtonGroup>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {visibleSeries.map((series) => (
        <AnalysisChart
          key={series}
          data={visiblePoints}
          mode={axisMode}
          series={series}
          color={seriesColors[series]}
          selection={selection}
          kilometerMarks={kilometerMarks}
          activeIndex={activeIndex}
          onHover={setActiveIndex}
        />
      ))}

      {routeWeather.length > 1 && (
        <WeatherRouteChart data={routeWeather} mode={axisMode} />
      )}

      <Card>
        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }} gap={1.5} sx={{ mb: 1.5 }}>
            <Box>
              <Stack direction="row" alignItems="center" spacing={1}>
                <ZoomOutMapRoundedIcon color="primary" />
                <Typography variant="h3">Zoomen & verschieben</Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary">Die Griffe begrenzen den sichtbaren Ausschnitt; die Mitte lässt sich verschieben.</Typography>
            </Box>
            <Stack direction="row" gap={1}>
              <Button size="small" startIcon={<SwapHorizRoundedIcon />} onClick={useVisibleAreaAsSection}>Als Abschnitt</Button>
              <Button
                size="small"
                startIcon={<RestartAltRoundedIcon />}
                disabled={safeZoomStart === 0 && safeZoomEnd === chartPoints.length - 1}
                onClick={() => setZoomRange([0, chartPoints.length - 1])}
              >Ansicht zurücksetzen</Button>
            </Stack>
          </Stack>
          <ResponsiveContainer width="100%" height={110}>
            <AreaChart data={chartPoints} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
              <XAxis dataKey={xKey} hide />
              <YAxis hide domain={['auto', 'auto']} />
              <Area dataKey="altitudeM" type="monotone" stroke={theme.palette.primary.main} fill={alpha(theme.palette.primary.main, .18)} connectNulls isAnimationActive={false} />
              <Brush
                dataKey={xKey}
                height={32}
                travellerWidth={14}
                startIndex={safeZoomStart}
                endIndex={safeZoomEnd}
                tickFormatter={(value) => formatAxisValue(Number(value), axisMode)}
                onChange={(range) => {
                  if (typeof range.startIndex === 'number' && typeof range.endIndex === 'number') {
                    setZoomRange([range.startIndex, range.endIndex])
                  }
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ p: { xs: 2, md: 2.5 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" gap={1.5} sx={{ mb: 2 }}>
            <Box>
              <Typography variant="h3">Streckenabschnitt</Typography>
              <Typography variant="body2" color="text.secondary">
                Ziehe Start und Ende frei auf der Strecke. Der ausgewählte Abschnitt wird auf Karte und Diagrammen blau hervorgehoben.
              </Typography>
            </Box>
            <Button
              color="inherit"
              startIcon={<RestartAltRoundedIcon />}
              disabled={!selection}
              onClick={() => setSelection(null)}
            >Auswahl zurücksetzen</Button>
          </Stack>
          <Box sx={{ px: { xs: 1, sm: 2 }, pt: 3, pb: 1 }}>
            <Slider
              min={0}
              max={Math.max(1, analysisPoints.length - 1)}
              step={1}
              value={fullSelection}
              disabled={analysisPoints.length < 2}
              disableSwap
              onChange={(_, value) => {
                if (Array.isArray(value)) {
                  const maximum = analysisPoints.length - 1
                  setSelection([
                    Math.min(maximum, Math.round(value[0])),
                    Math.min(maximum, Math.round(value[1])),
                  ])
                }
              }}
              valueLabelDisplay="on"
              valueLabelFormat={(index) => {
                const point = analysisPoints[Math.min(Number(index), analysisPoints.length - 1)]
                return point ? formatAxisValue(point[xKey] as number, axisMode) : '–'
              }}
              aria-label="Streckenabschnitt auswählen"
            />
          </Box>

          {selectionMetrics ? (
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', sm: 'repeat(3, minmax(0, 1fr))', xl: 'repeat(5, minmax(0, 1fr))' }, gap: 1.25, mt: 1 }}>
              <SectionMetric label="Distanz" value={formatSectionDistance(selectionMetrics.distanceM)} icon={<RouteRoundedIcon fontSize="small" />} />
              <SectionMetric label="Dauer" value={formatElapsed(selectionMetrics.durationSeconds)} icon={<AccessTimeRoundedIcon fontSize="small" />} />
              <SectionMetric label="Ø Geschwindigkeit" value={formatSpeed(selectionMetrics.averageSpeedKmh)} icon={<SpeedRoundedIcon fontSize="small" />} />
              <SectionMetric label="Max. Geschwindigkeit" value={formatSpeed(selectionMetrics.maximumSpeedKmh)} icon={<SpeedRoundedIcon fontSize="small" />} />
              <SectionMetric label="Ø Herzfrequenz" value={formatHeartRate(selectionMetrics.averageHeartRateBpm)} icon={<FavoriteRoundedIcon fontSize="small" />} />
              <SectionMetric label="Max. Herzfrequenz" value={formatHeartRate(selectionMetrics.maximumHeartRateBpm)} icon={<FavoriteRoundedIcon fontSize="small" />} />
              <SectionMetric label="Höhengewinn" value={formatElevation(selectionMetrics.elevationGainM)} icon={<LandscapeRoundedIcon fontSize="small" />} />
              <SectionMetric label="Höhenverlust" value={formatElevation(selectionMetrics.elevationLossM)} icon={<LandscapeRoundedIcon fontSize="small" />} />
              <SectionMetric label="Ø Steigung" value={formatGradient(selectionMetrics.averageGradientPercent)} icon={<TerrainRoundedIcon fontSize="small" />} />
              <SectionMetric label="Max. Steigung" value={formatGradient(selectionMetrics.maximumGradientPercent)} icon={<TerrainRoundedIcon fontSize="small" />} />
            </Box>
          ) : (
            <Box sx={{ mt: 1, p: 2, borderRadius: 2.5, bgcolor: alpha(theme.palette.primary.main, .06), color: 'text.secondary' }}>
              Bewege einen der beiden Regler oder übernimm den sichtbaren Diagrammausschnitt, um einen Abschnitt auszuwerten.
            </Box>
          )}
        </CardContent>
      </Card>
    </Stack>
  )
}
