export interface RideFixture {
  title: string
  type: string
  daysAgo: number
  distanceKm: number
  gps?: boolean
  sensors?: boolean
  notes?: string
  hydrationMl?: number
}

export const rides: RideFixture[] = [
  { title: 'Morgenrunde am See', type: 'training', daysAgo: 1, distanceKm: 42, gps: true, sensors: true, notes: 'Ruhiger Start, danach gleichmäßiger Druck.', hydrationMl: 750 },
  { title: 'Sehr lange deutsche Aktivitätsbezeichnung für die responsive Darstellung ohne abgeschnittene Hauptinformation', type: 'tour', daysAgo: 3, distanceKm: 64, gps: true, sensors: true },
  { title: 'Indoor-Intervalle ohne GPS', type: 'indoor', daysAgo: 6, distanceKm: 28, gps: false, sensors: true },
  { title: 'Feierabendrunde', type: 'commute', daysAgo: 11, distanceKm: 19, gps: true, sensors: false },
  { title: 'Grundlage im Wind', type: 'training', daysAgo: 18, distanceKm: 53, gps: true, sensors: true },
  { title: 'Kurze Kaffeerunde', type: 'ride', daysAgo: 26, distanceKm: 12, gps: true, sensors: false },
  { title: 'Hügeltraining', type: 'training', daysAgo: 40, distanceKm: 36, gps: true, sensors: true },
  { title: 'Lange Sonntagsrunde', type: 'tour', daysAgo: 65, distanceKm: 78, gps: true, sensors: true },
  { title: 'Regenerationsfahrt', type: 'ride', daysAgo: 94, distanceKm: 22, gps: true, sensors: true },
  { title: 'Frühlingsklassiker', type: 'tour', daysAgo: 185, distanceKm: 91, gps: true, sensors: true },
  { title: 'Vorjahresvergleich schnell', type: 'training', daysAgo: 370, distanceKm: 47, gps: true, sensors: true },
  { title: 'Vorjahresvergleich lang', type: 'tour', daysAgo: 390, distanceKm: 82, gps: true, sensors: true },
]

function isoWithoutMilliseconds(value: Date) {
  return value.toISOString().replace('.000Z', 'Z')
}

export function fixtureDate(daysAgo: number) {
  const value = new Date('2026-07-14T08:00:00Z')
  value.setUTCDate(value.getUTCDate() - daysAgo)
  return value
}

export function tcxForRide(ride: RideFixture) {
  const startedAt = fixtureDate(ride.daysAgo)
  const durationSeconds = Math.round(ride.distanceKm * 145)
  const pointCount = Math.ceil(durationSeconds / 90) + 1
  const stepSeconds = durationSeconds / (pointCount - 1)
  const points = Array.from({ length: pointCount }, (_, index) => {
    const ratio = index / (pointCount - 1)
    const time = new Date(startedAt.getTime() + Math.round(index * stepSeconds * 1000))
    const latitude = 52.48 + ratio * .12 + Math.sin(ratio * Math.PI * 4) * .012
    const longitude = 13.31 + ratio * .18 + Math.cos(ratio * Math.PI * 3) * .016
    const distance = Math.round(ride.distanceKm * 1000 * ratio)
    const altitude = Math.round(72 + ratio * 95 + Math.sin(ratio * Math.PI * 6) * 28)
    const sensorXml = ride.sensors === false ? '' : `<HeartRateBpm><Value>${Math.round(112 + ratio * 52)}</Value></HeartRateBpm><Cadence>${Math.round(68 + ratio * 24)}</Cadence><Extensions><ns3:TPX><ns3:Speed>${(ride.distanceKm * 1000 / durationSeconds).toFixed(2)}</ns3:Speed><ns3:Watts>${Math.round(125 + ratio * 115)}</ns3:Watts></ns3:TPX></Extensions>`
    const positionXml = ride.gps === false ? '' : `<Position><LatitudeDegrees>${latitude.toFixed(6)}</LatitudeDegrees><LongitudeDegrees>${longitude.toFixed(6)}</LongitudeDegrees></Position>`
    return `<Trackpoint><Time>${isoWithoutMilliseconds(time)}</Time>${positionXml}<AltitudeMeters>${altitude}</AltitudeMeters><DistanceMeters>${distance}</DistanceMeters>${sensorXml}</Trackpoint>`
  }).join('')
  return `<?xml version="1.0" encoding="UTF-8"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2"><Activities><Activity Sport="Biking"><Id>${isoWithoutMilliseconds(startedAt)}</Id><Lap StartTime="${isoWithoutMilliseconds(startedAt)}"><Track>${points}</Track></Lap></Activity></Activities></TrainingCenterDatabase>`
}
