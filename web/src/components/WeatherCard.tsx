import AirRoundedIcon from '@mui/icons-material/AirRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import ThermostatRoundedIcon from '@mui/icons-material/ThermostatRounded'
import WaterDropRoundedIcon from '@mui/icons-material/WaterDropRounded'
import WbSunnyRoundedIcon from '@mui/icons-material/WbSunnyRounded'
import { Alert, alpha, Button, Card, CardContent, Chip, Divider, Skeleton, Stack, Typography } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { activitiesApi, type WeatherData } from '../api'
import { errorMessage, formatDateTime } from '../utils/format'

export function WeatherCard({ activityId, fallback }: { activityId: string; fallback?: WeatherData | null }) {
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ['activity', activityId, 'weather'],
    queryFn: () => activitiesApi.weather(activityId),
    retry: false,
  })
  const refresh = useMutation({
    mutationFn: () => activitiesApi.refreshWeather(activityId),
    onSuccess: (data) => client.setQueryData(['activity', activityId, 'weather'], data),
  })
  const weather = query.data?.data ?? fallback
  const humidity = weather?.relative_humidity_percent ?? weather?.humidity_percent
  const feelsLike = weather?.apparent_temperature_c ?? weather?.feels_like_c
  const routeWind = weather?.route_wind && typeof weather.route_wind === 'object'
    ? weather.route_wind as Record<string, unknown>
    : undefined
  const netHeadwind = typeof routeWind?.net_headwind_kmh === 'number' ? routeWind.net_headwind_kmh : null

  return (
    <Card sx={{ height: '100%', background: (theme) => `linear-gradient(150deg, ${alpha(theme.palette.chart.blue, .08)}, ${theme.palette.background.paper})` }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={2}>
          <Stack direction="row" spacing={1.25} alignItems="center">
            <WbSunnyRoundedIcon sx={{ color: 'chart.amber', fontSize: 32 }} />
            <div><Typography variant="h3">Wetter</Typography><Typography variant="body2" color="text.secondary">Bedingungen auf der Strecke</Typography></div>
          </Stack>
          {query.data?.status && <Chip size="small" label={query.data.status === 'available' || query.data.status === 'ready' ? 'Ermittelt' : query.data.status} />}
        </Stack>
        <Divider sx={{ my: 2 }} />
        {query.isLoading && !fallback ? <Skeleton variant="rounded" height={120} /> : weather ? (
          <>
            <Stack direction="row" alignItems="baseline" spacing={1} sx={{ mb: 2 }}>
              <Typography variant="h2">{weather.temperature_c == null ? '–' : `${Math.round(weather.temperature_c)}°`}</Typography>
              <Typography color="text.secondary">{weather.condition || weatherLabel(weather.weather_code)}</Typography>
            </Stack>
            <Stack direction="row" flexWrap="wrap" gap={1.5}>
              <WeatherMetric icon={<ThermostatRoundedIcon />} label="Gefühlt" value={feelsLike == null ? '–' : `${Math.round(feelsLike)} °C`} />
              <WeatherMetric icon={<AirRoundedIcon />} label="Wind" value={weather.wind_speed_kmh == null ? '–' : `${Math.round(weather.wind_speed_kmh)} km/h${weather.wind_direction_deg == null ? '' : ` aus ${windDirection(weather.wind_direction_deg)}`}`} />
              <WeatherMetric icon={<AirRoundedIcon />} label="Auf der Strecke" value={windImpact(netHeadwind)} />
              <WeatherMetric icon={<WaterDropRoundedIcon />} label="Feuchte" value={humidity == null ? '–' : `${Math.round(humidity)} %`} />
            </Stack>
            {query.data?.updated_at && <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>Aktualisiert {formatDateTime(query.data.updated_at)}</Typography>}
          </>
        ) : (
          <Stack spacing={1.5}>
            <Typography color="text.secondary">Für diese Fahrt liegen noch keine Wetterdaten vor.</Typography>
            <Button variant="outlined" onClick={() => refresh.mutate()} disabled={refresh.isPending} startIcon={<RefreshRoundedIcon />}>Wetter abrufen</Button>
          </Stack>
        )}
        {(query.isError || refresh.isError) && <Alert severity="warning" sx={{ mt: 2 }}>{errorMessage(query.error ?? refresh.error)}</Alert>}
        {weather && <Button size="small" sx={{ mt: 1.5 }} onClick={() => refresh.mutate()} disabled={refresh.isPending} startIcon={<RefreshRoundedIcon />}>{refresh.isPending ? 'Wird aktualisiert …' : 'Aktualisieren'}</Button>}
      </CardContent>
    </Card>
  )
}

function windDirection(degrees: number) {
  const labels = ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW']
  const normalized = ((degrees % 360) + 360) % 360
  return `${labels[Math.round(normalized / 45) % labels.length]} (${Math.round(normalized)}°)`
}

function windImpact(value: number | null) {
  if (value == null) return 'Noch nicht berechnet'
  if (value >= 1) return `${value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} km/h Gegenwind`
  if (value <= -1) return `${Math.abs(value).toLocaleString('de-DE', { maximumFractionDigits: 1 })} km/h Rückenwind`
  return 'Ausgeglichen'
}

function WeatherMetric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <Stack direction="row" spacing={.8} alignItems="center" sx={{ color: 'text.secondary', '& svg': { fontSize: 18 } }}><>{icon}</><div><Typography variant="caption">{label}</Typography><Typography variant="body2" fontWeight={750} color="text.primary">{value}</Typography></div></Stack>
}

function weatherLabel(code?: number | null) {
  if (code == null) return 'Wetterdaten'
  if (code === 0) return 'Klar'
  if (code <= 3) return 'Bewölkt'
  if (code <= 48) return 'Neblig'
  if (code <= 67) return 'Regen'
  if (code <= 77) return 'Schnee'
  return 'Wechselhaft'
}
