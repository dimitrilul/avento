import type { ApiErrorBody, TokenResponse } from './types'

const API_URL = (import.meta.env.VITE_API_URL ?? '/api/v1').replace(/\/$/, '')
const TOKEN_KEY = 'avento.auth.tokens'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body?: ApiErrorBody,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function getStoredTokens(): TokenResponse | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY)
    return raw ? (JSON.parse(raw) as TokenResponse) : null
  } catch {
    return null
  }
}

export const tokenStore = {
  get: getStoredTokens,
  set(tokens: TokenResponse) {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
    window.dispatchEvent(new CustomEvent('avento:auth-changed'))
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    window.dispatchEvent(new CustomEvent('avento:auth-changed'))
  },
}

async function readError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | undefined
  try {
    body = (await response.json()) as ApiErrorBody
  } catch {
    body = undefined
  }
  const detail = body?.detail
  const message =
    typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((entry) => entry.msg).filter(Boolean).join(', ')
        : body?.message || `Anfrage fehlgeschlagen (${response.status})`
  return new ApiError(message, response.status, body)
}

let refreshPromise: Promise<TokenResponse> | null = null

async function refreshTokens(): Promise<TokenResponse> {
  const tokens = tokenStore.get()
  if (!tokens?.refresh_token) throw new ApiError('Sitzung abgelaufen', 401)
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  })
  if (!response.ok) {
    tokenStore.clear()
    throw await readError(response)
  }
  const next = (await response.json()) as TokenResponse
  tokenStore.set(next)
  return next
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  auth?: boolean
  retry?: boolean
}

function requestUrl(path: string) {
  if (/^(https?:|blob:|data:)/i.test(path)) return path
  if (path.startsWith('/api/')) return path
  if (path.startsWith(API_URL)) return path
  return `${API_URL}${path.startsWith('/') ? path : `/${path}`}`
}

function isTrustedApiTarget(target: string) {
  if (/^(blob:|data:)/i.test(target)) return false
  const targetUrl = new URL(target, window.location.origin)
  const apiBase = new URL(API_URL, window.location.origin)
  return targetUrl.origin === apiBase.origin && targetUrl.pathname.startsWith(apiBase.pathname)
}

async function apiResponse(path: string, options: RequestOptions = {}): Promise<Response> {
  const { body, auth = true, retry = true, headers: providedHeaders, ...init } = options
  const headers = new Headers(providedHeaders)
  const tokens = tokenStore.get()
  const isFormData = body instanceof FormData
  const target = requestUrl(path)
  const trustedTarget = isTrustedApiTarget(target)
  if (body !== undefined && !isFormData) headers.set('Content-Type', 'application/json')
  if (auth && trustedTarget && tokens?.access_token) headers.set('Authorization', `Bearer ${tokens.access_token}`)

  const response = await fetch(target, {
    ...init,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  })

  if (response.status === 401 && auth && trustedTarget && retry && tokens?.refresh_token) {
    try {
      refreshPromise ??= refreshTokens().finally(() => {
        refreshPromise = null
      })
      await refreshPromise
      return apiResponse(path, { ...options, retry: false })
    } catch (error) {
      tokenStore.clear()
      throw error
    }
  }

  if (!response.ok) throw await readError(response)
  return response
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await apiResponse(path, options)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function apiBlobRequest(path: string, options: RequestOptions = {}): Promise<Blob> {
  const response = await apiResponse(path, options)
  return response.blob()
}

export function apiUploadRequest<T>(
  path: string,
  body: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  if (!onProgress) return apiRequest<T>(path, { method: 'POST', body })
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', requestUrl(path))
    const tokens = tokenStore.get()
    const target = requestUrl(path)
    if (tokens?.access_token && isTrustedApiTarget(target)) {
      xhr.setRequestHeader('Authorization', `Bearer ${tokens.access_token}`)
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100))
    }
    xhr.onerror = () => reject(new ApiError('Upload fehlgeschlagen', 0))
    xhr.onload = () => {
      let payload: unknown
      try { payload = xhr.responseText ? JSON.parse(xhr.responseText) : undefined } catch { payload = undefined }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(payload as T)
      const detail = (payload as ApiErrorBody | undefined)?.detail
      const message = typeof detail === 'string' ? detail : `Upload fehlgeschlagen (${xhr.status})`
      reject(new ApiError(message, xhr.status, payload as ApiErrorBody | undefined))
    }
    xhr.send(body)
  })
}

export const apiUrl = API_URL
