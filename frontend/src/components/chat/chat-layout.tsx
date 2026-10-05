import { useCallback, useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/use-auth'
import { ThreadSidebar } from '@/components/chat/thread-sidebar'
import { api } from '@/lib/api'
import type { ChatLayoutContext, ChatThread } from '@/lib/chat'

function newestFirst(threads: ChatThread[]) {
  return [...threads].sort(
    (left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at),
  )
}

export function ChatLayout() {
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [isLoadingThreads, setIsLoadingThreads] = useState(true)
  const [isCreatingThread, setIsCreatingThread] = useState(false)
  const [threadsError, setThreadsError] = useState<string | null>(null)

  const refreshThreads = useCallback(async () => {
    try {
      const nextThreads = await api.chat.listThreads()
      setThreads(newestFirst(nextThreads))
      setThreadsError(null)
    } catch (error) {
      setThreadsError(error instanceof Error ? error.message : 'Unable to load conversations')
    } finally {
      setIsLoadingThreads(false)
    }
  }, [])

  useEffect(() => {
    let isCurrent = true

    void api.chat
      .listThreads()
      .then((nextThreads) => {
        if (!isCurrent) return
        setThreads(newestFirst(nextThreads))
        setThreadsError(null)
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setThreadsError(error instanceof Error ? error.message : 'Unable to load conversations')
        }
      })
      .finally(() => {
        if (isCurrent) setIsLoadingThreads(false)
      })

    return () => {
      isCurrent = false
    }
  }, [])

  async function createThread() {
    setIsCreatingThread(true)
    setThreadsError(null)
    try {
      const thread = await api.chat.createThread()
      setThreads((current) => newestFirst([thread, ...current]))
      navigate(`/chat/${thread.id}`)
    } catch (error) {
      setThreadsError(error instanceof Error ? error.message : 'Unable to create conversation')
    } finally {
      setIsCreatingThread(false)
    }
  }

  const outletContext: ChatLayoutContext = {
    threads,
    isLoadingThreads,
    threadsError,
    isCreatingThread,
    createThread,
    refreshThreads,
  }

  return (
    <main className="flex min-h-svh flex-col bg-muted/30 md:grid md:h-svh md:grid-cols-[18rem_minmax(0,1fr)] md:overflow-hidden">
      <ThreadSidebar
        threads={threads}
        isLoading={isLoadingThreads}
        error={threadsError}
        isCreating={isCreatingThread}
        onCreate={() => void createThread()}
        onSignOut={() => void signOut()}
      />
      <section className="min-h-[65svh] min-w-0 bg-background md:min-h-0">
        <Outlet context={outletContext} />
      </section>
    </main>
  )
}
