import type { UIMessage } from 'ai'

export type ChatThread = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export type StoredChatMessage = UIMessage & {
  created_at?: string
}

export type ChatLayoutContext = {
  threads: ChatThread[]
  isLoadingThreads: boolean
  threadsError: string | null
  isCreatingThread: boolean
  createThread: () => Promise<void>
  refreshThreads: () => Promise<void>
}
