import { apiBlobRequest, apiRequest } from './client'
import type {
  ActivityPhoto,
  ActivityPhotoListResponse,
  ActivityPhotoUpdate,
  ActivityPhotoUpload,
  LongTermInsightsResponse,
  McpAccessToken,
  McpAccessTokenRequest,
  McpAuditEvent,
  McpClient,
  McpClientCreate,
  McpClientCreated,
  McpClientUpdate,
  McpSecretRotated,
  PersonalRecordsResponse,
  PeriodReviewResponse,
} from './types'

function queryString(values: Record<string, string | number | undefined>) {
  const query = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

export const activityPhotosApi = {
  list: (activityId: string) =>
    apiRequest<ActivityPhotoListResponse>(`/activities/${activityId}/photos`),
  upload: (activityId: string, data: ActivityPhotoUpload) => {
    const form = new FormData()
    form.set('file', data.file)
    if (data.caption?.trim()) form.set('caption', data.caption.trim())
    if (data.captured_at) form.set('captured_at', data.captured_at)
    if (data.latitude != null) form.set('latitude', String(data.latitude))
    if (data.longitude != null) form.set('longitude', String(data.longitude))
    return apiRequest<ActivityPhoto>(`/activities/${activityId}/photos`, {
      method: 'POST',
      body: form,
    })
  },
  update: (activityId: string, photoId: string, data: ActivityPhotoUpdate) =>
    apiRequest<ActivityPhoto>(`/activities/${activityId}/photos/${photoId}`, {
      method: 'PATCH',
      body: data,
    }),
  delete: (activityId: string, photoId: string) =>
    apiRequest<void>(`/activities/${activityId}/photos/${photoId}`, { method: 'DELETE' }),
  file: (photo: ActivityPhoto) => apiBlobRequest(photo.file_url),
}

export const insightsApi = {
  records: () => apiRequest<PersonalRecordsResponse>('/statistics/records'),
  longTerm: (dateFrom?: string, dateTo?: string) =>
    apiRequest<LongTermInsightsResponse>(
      `/statistics/insights${queryString({ date_from: dateFrom, date_to: dateTo })}`,
    ),
  periodReview: (year: number, season = 'year') =>
    apiRequest<PeriodReviewResponse>(
      `/statistics/reviews/${year}${queryString({ season })}`,
    ),
}

export const mcpAdminApi = {
  clients: () => apiRequest<McpClient[]>('/mcp/clients'),
  createClient: (data: McpClientCreate) =>
    apiRequest<McpClientCreated>('/mcp/clients', { method: 'POST', body: data }),
  updateClient: (clientId: string, data: McpClientUpdate) =>
    apiRequest<McpClient>(`/mcp/clients/${clientId}`, { method: 'PATCH', body: data }),
  rotateSecret: (clientId: string) =>
    apiRequest<McpSecretRotated>(`/mcp/clients/${clientId}/rotate-secret`, { method: 'POST' }),
  revokeClient: (clientId: string) =>
    apiRequest<McpClient>(`/mcp/clients/${clientId}/revoke`, { method: 'POST' }),
  revokeTokens: (clientId: string) =>
    apiRequest<void>(`/mcp/clients/${clientId}/tokens/revoke`, { method: 'POST' }),
  requestToken: (data: McpAccessTokenRequest) =>
    apiRequest<McpAccessToken>('/mcp/token', { method: 'POST', body: data, auth: false }),
  auditLog: (limit = 100) =>
    apiRequest<McpAuditEvent[]>(`/mcp/audit${queryString({ limit })}`),
}
