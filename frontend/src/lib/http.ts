import { env } from '@/lib/env'

const REQUEST_TIMEOUT_MS = 15_000

export class ApiError extends Error {
  readonly status: number | null
  readonly isNetworkError: boolean

  constructor(
    message: string,
    status: number | null,
    isNetworkError: boolean,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  accessToken?: string
  body?: unknown
}

export async function request<T>(
  path: string,
  { accessToken, body, headers, ...init }: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...init,
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...headers,
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        detail?: string
      } | null
      throw new ApiError(
        payload?.detail ?? `Request failed with status ${response.status}`,
        response.status,
        false,
      )
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error

    const message =
      error instanceof DOMException && error.name === 'AbortError'
        ? 'The request timed out'
        : 'Unable to reach the server'
    throw new ApiError(message, null, true)
  } finally {
    window.clearTimeout(timeout)
  }
}
