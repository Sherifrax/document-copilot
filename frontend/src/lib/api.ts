import { request } from '@/lib/http'
import { supabase } from '@/lib/supabase'

async function authenticatedRequest<T>(
  path: string,
  init?: Omit<Parameters<typeof request<T>>[1], 'accessToken'>,
): Promise<T> {
  const { data, error } = await supabase.auth.getSession()
  if (error || !data.session) {
    throw new Error('You must be signed in to make this request')
  }

  return request<T>(path, { ...init, accessToken: data.session.access_token })
}

export const api = {
  get: <T>(path: string) => authenticatedRequest<T>(path),
  post: <T>(path: string, body?: unknown) =>
    authenticatedRequest<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) =>
    authenticatedRequest<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) =>
    authenticatedRequest<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) =>
    authenticatedRequest<T>(path, { method: 'DELETE' }),
}
