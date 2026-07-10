import { describe, expect, it, vi } from 'vitest'
import type { TrackPoint } from '../api'
import { buildAnalysisPoints, calculateSectionMetrics } from './AdvancedActivityAnalysis'

vi.mock('./TrackMap', () => ({ TrackMap: () => null }))

const points: TrackPoint[] = [
  {
    time: '2026-07-10T08:00:00Z',
    latitude: 52,
    longitude: 13,
    altitude_m: 100,
    distance_m: 0,
    speed_mps: 5,
    heart_rate_bpm: 100,
  },
  {
    time: '2026-07-10T08:01:00Z',
    latitude: 52.001,
    longitude: 13.001,
    altitude_m: 120,
    distance_m: 1_000,
    speed_mps: 10,
    heart_rate_bpm: 140,
  },
  {
    time: '2026-07-10T08:02:00Z',
    latitude: 52.002,
    longitude: 13.002,
    altitude_m: 110,
    distance_m: 2_000,
    speed_mps: 8,
    heart_rate_bpm: 160,
  },
]

describe('buildAnalysisPoints', () => {
  it('normalisiert Distanz, Zeit und Geschwindigkeit für die Diagramme', () => {
    const result = buildAnalysisPoints(points)

    expect(result).toHaveLength(3)
    expect(result[1]).toMatchObject({
      index: 1,
      distanceM: 1_000,
      distanceKm: 1,
      elapsedSeconds: 60,
      speedKmh: 36,
      heartRateBpm: 140,
    })
  })

  it('berechnet bei fehlender Distanz eine GPS-basierte Ersatzdistanz', () => {
    const result = buildAnalysisPoints(points.map((point) => ({ ...point, distance_m: null })))

    expect(result[1].distanceM).toBeGreaterThan(100)
    expect(result[2].distanceM).toBeGreaterThan(result[1].distanceM)
  })
})

describe('calculateSectionMetrics', () => {
  it('berechnet alle Kennzahlen des frei gewählten Abschnitts', () => {
    const result = calculateSectionMetrics(buildAnalysisPoints(points), 0, 2)

    expect(result).not.toBeNull()
    expect(result?.distanceM).toBe(2_000)
    expect(result?.durationSeconds).toBe(120)
    expect(result?.averageSpeedKmh).toBeCloseTo(60)
    expect(result?.maximumSpeedKmh).toBe(36)
    expect(result?.averageHeartRateBpm).toBeCloseTo(133.33, 2)
    expect(result?.maximumHeartRateBpm).toBe(160)
    expect(result?.elevationGainM).toBe(20)
    expect(result?.elevationLossM).toBe(10)
    expect(result?.averageGradientPercent).toBeCloseTo(.5)
    expect(result?.maximumGradientPercent).toBeCloseTo(2)
  })
})
