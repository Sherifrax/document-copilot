import { request } from '@/lib/http'
import { supabase } from '@/lib/supabase'
import type { ChatThread, StoredChatMessage } from '@/lib/chat'

export async function getAccessToken(): Promise<string> {
  const { data, error } = await supabase.auth.getSession()
  if (error || !data.session) {
    throw new Error('You must be signed in to make this request')
  }

  return data.session.access_token
}

async function authenticatedRequest<T>(
  path: string,
  init?: Omit<Parameters<typeof request<T>>[1], 'accessToken'>,
): Promise<T> {
  return request<T>(path, { ...init, accessToken: await getAccessToken() })
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
  chat: {
    listThreads: () => authenticatedRequest<ChatThread[]>('/chat/threads'),
    createThread: () =>
      authenticatedRequest<ChatThread>('/chat/threads', {
        method: 'POST',
        body: { title: 'New conversation' },
      }),
    getMessages: (threadId: string) =>
      authenticatedRequest<StoredChatMessage[]>(`/chat/threads/${threadId}/messages`),
  },
}
