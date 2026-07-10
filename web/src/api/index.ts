import { apiRequest, tokenStore } from './client'
import type {
  Activity,
  ActivityComparison,
  ActivityDetail,
  ActivityFilters,
  ActivityUpdate,
  BootstrapData,
  ImportActivityData,
  InvitationResponse,
  PasswordResetResponse,
  PaginatedActivities,
  Profile,
  RegistrationData,
  StatisticsOverview,
  TokenResponse,
  TrackResponse,
  WeatherResponse,
  SummaryResponse,
} from './types'

function queryString(values: Record<string, string | number | undefined>) {
  const query = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value))
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

export const authApi = {
  async login(email: string, password: string) {
    const tokens = await apiRequest<TokenResponse>('/auth/login', {
      method: 'POST',
      auth: false,
      body: { email, password },
    })
    tokenStore.set(tokens)
    return tokens
  },
  async register(data: RegistrationData) {
    const tokens = await apiRequest<TokenResponse>('/auth/register', {
      method: 'POST',
      auth: false,
      body: data,
    })
    tokenStore.set(tokens)
    return tokens
  },
  async bootstrap(data: BootstrapData) {
    const tokens = await apiRequest<TokenResponse>('/auth/bootstrap', {
      method: 'POST',
      auth: false,
      body: data,
    })
    tokenStore.set(tokens)
    return tokens
  },
  async logout() {
    const refreshToken = tokenStore.get()?.refresh_token
    try {
      if (refreshToken) {
        await apiRequest<void>('/auth/logout', {
          method: 'POST',
          body: { refresh_token: refreshToken },
        })
      }
    } finally {
      tokenStore.clear()
    }
  },
  createInvitation: (email?: string, expiresInDays = 7) =>
    apiRequest<InvitationResponse>('/auth/invitations', {
      method: 'POST',
      body: { email: email || null, expires_in_days: expiresInDays },
    }),
  createPasswordReset: (email: string, expiresInMinutes = 60) =>
    apiRequest<PasswordResetResponse>('/auth/password-resets', {
      method: 'POST',
      body: { email, expires_in_minutes: expiresInMinutes },
    }),
  resetPassword: (token: string, newPassword: string) =>
    apiRequest<void>('/auth/password-reset', {
      method: 'POST',
      auth: false,
      body: { token, new_password: newPassword },
    }),
}

export const profileApi = {
  get: () => apiRequest<Profile>('/profile'),
  update: (data: Partial<Omit<Profile, 'id' | 'email'>>) =>
    apiRequest<Profile>('/profile', { method: 'PATCH', body: data }),
  changePassword: (currentPassword: string, newPassword: string) =>
    apiRequest<void>('/profile/password', {
      method: 'POST',
      body: { current_password: currentPassword, new_password: newPassword },
    }),
}

export const activitiesApi = {
  list: (filters: ActivityFilters = {}) =>
    apiRequest<PaginatedActivities>(
      `/activities${queryString({
        limit: filters.limit ?? 50,
        offset: filters.offset ?? 0,
        q: filters.q,
        type: filters.type,
        date_from: filters.date_from,
        date_to: filters.date_to,
      })}`,
    ),
  get: (id: string) => apiRequest<ActivityDetail>(`/activities/${id}`),
  import: (data: ImportActivityData) => {
    const form = new FormData()
    form.set('file', data.file)
    if (data.title) form.set('title', data.title)
    if (data.type) form.set('type', data.type)
    if (data.notes) form.set('notes', data.notes)
    return apiRequest<Activity>('/activities', { method: 'POST', body: form })
  },
  update: (id: string, data: ActivityUpdate) =>
    apiRequest<ActivityDetail>(`/activities/${id}`, { method: 'PATCH', body: data }),
  reanalyze: (id: string) =>
    apiRequest<ActivityDetail>(`/activities/${id}/reanalyze`, { method: 'POST' }),
  delete: (id: string) => apiRequest<void>(`/activities/${id}`, { method: 'DELETE' }),
  track: (id: string) => apiRequest<TrackResponse>(`/activities/${id}/track`),
  weather: (id: string) => apiRequest<WeatherResponse>(`/activities/${id}/weather`),
  refreshWeather: (id: string) =>
    apiRequest<WeatherResponse>(`/activities/${id}/weather/refresh`, { method: 'POST' }),
  summary: (id: string) => apiRequest<SummaryResponse>(`/activities/${id}/summary`),
  generateSummary: (id: string, force = false) =>
    apiRequest<SummaryResponse>(`/activities/${id}/summary?force=${force}`, { method: 'POST' }),
  compare: (activityIds: string[]) =>
    apiRequest<ActivityComparison>('/activities/compare', {
      method: 'POST',
      body: { activity_ids: activityIds },
    }),
}

export const statisticsApi = {
  overview: (dateFrom?: string, dateTo?: string) =>
    apiRequest<StatisticsOverview>(
      `/statistics/overview${queryString({ date_from: dateFrom, date_to: dateTo })}`,
    ),
}

export type * from './types'
