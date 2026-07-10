import { useEffect, useRef } from 'react'
import LocationOffRoundedIcon from '@mui/icons-material/LocationOffRounded'
import { Box, Stack, Typography } from '@mui/material'
import maplibregl from 'maplibre-gl'
import type { TrackPoint } from '../api'

const mapStyle = import.meta.env.VITE_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/liberty'

export function TrackMap({ points }: { points: TrackPoint[] }) {
  const container = useRef<HTMLDivElement>(null)
  const coordinates = points
    .filter((point): point is TrackPoint & { longitude: number; latitude: number } => typeof point.longitude === 'number' && typeof point.latitude === 'number')
    .map((point) => [point.longitude, point.latitude] as [number, number])

  useEffect(() => {
    if (!container.current || coordinates.length < 2) return
    const map = new maplibregl.Map({
      container: container.current,
      style: mapStyle,
      center: coordinates[0],
      zoom: 11,
      attributionControl: false,
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
    map.on('load', () => {
      map.addSource('route', {
        type: 'geojson',
        data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates } },
      })
      map.addLayer({
        id: 'route-glow',
        type: 'line',
        source: 'route',
        paint: { 'line-color': '#FFFFFF', 'line-width': 8, 'line-opacity': .86 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      })
      map.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'route',
        paint: { 'line-color': '#0E6562', 'line-width': 4 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      })
      new maplibregl.Marker({ color: '#A5C838' }).setLngLat(coordinates[0]).addTo(map)
      new maplibregl.Marker({ color: '#E26D5A' }).setLngLat(coordinates.at(-1)!).addTo(map)
      const bounds = coordinates.reduce((current, coordinate) => current.extend(coordinate), new maplibregl.LngLatBounds(coordinates[0], coordinates[0]))
      map.fitBounds(bounds, { padding: 52, maxZoom: 15, duration: 0 })
    })
    return () => map.remove()
  }, [points]) // eslint-disable-line react-hooks/exhaustive-deps

  if (coordinates.length < 2) {
    return (
      <Stack alignItems="center" justifyContent="center" spacing={1} sx={{ height: 420, bgcolor: 'background.default' }}>
        <LocationOffRoundedIcon color="disabled" fontSize="large" />
        <Typography color="text.secondary">Diese Aktivität enthält keine GPS-Strecke.</Typography>
      </Stack>
    )
  }

  return <Box ref={container} aria-label="Karte der gefahrenen Strecke" sx={{ width: '100%', height: { xs: 340, md: 440 } }} />
}
