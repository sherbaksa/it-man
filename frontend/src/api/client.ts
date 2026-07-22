/** Author: Dev2 | Date: 2026-07-22 | Purpose: Shared HTTP client with JWT refresh and API error mapping. */
import axios, { AxiosHeaders, isAxiosError, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { components } from './types'

type AccessTokenResponse = components['schemas']['AccessTokenResponse']
type ValidationError = components['schemas']['ValidationError']
type RetriableRequest = InternalAxiosRequestConfig & { _retry?: boolean }

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
export const apiBaseUrl = (configuredBaseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '')

let accessToken: string | null = null
let refreshRequest: Promise<string> | null = null
let accessTokenListener: ((token: string | null) => void) | null = null
let authenticationFailureHandler: (() => void) | null = null

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

export function setApiAccessToken(token: string | null) {
  accessToken = token
  accessTokenListener?.(token)
}

export function registerAccessTokenListener(listener: (token: string | null) => void) {
  accessTokenListener = listener
}

export function registerAuthenticationFailureHandler(handler: () => void) {
  authenticationFailureHandler = handler
}

function isAuthenticationRequest(url?: string) {
  return url?.includes('/api/auth/login') || url?.includes('/api/auth/refresh')
}

export async function refreshApiAccessToken() {
  if (!refreshRequest) {
    refreshRequest = axios
      .post<AccessTokenResponse>(`${apiBaseUrl}/api/auth/refresh`, undefined, { withCredentials: true })
      .then(({ data }) => {
        setApiAccessToken(data.access_token)
        return data.access_token
      })
      .finally(() => {
        refreshRequest = null
      })
  }

  return refreshRequest
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = AxiosHeaders.from(config.headers)
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as RetriableRequest | undefined
    if (error.response?.status !== 401 || !request || request._retry || isAuthenticationRequest(request.url)) {
      return Promise.reject(error)
    }

    request._retry = true
    try {
      const token = await refreshApiAccessToken()
      request.headers = AxiosHeaders.from(request.headers)
      request.headers.set('Authorization', `Bearer ${token}`)
      return apiClient(request)
    } catch (refreshError) {
      setApiAccessToken(null)
      authenticationFailureHandler?.()
      return Promise.reject(refreshError)
    }
  },
)

export function getApiErrorMessage(error: unknown, fallback: string) {
  if (!isAxiosError(error)) return error instanceof Error ? error.message : fallback

  const detail = (error.response?.data as { detail?: string | ValidationError[] } | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join('; ') || fallback
  return fallback
}
