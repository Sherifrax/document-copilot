import { useCallback, useEffect, useState } from 'react'
import { Menu, Plus } from 'lucide-react'
import { Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/use-auth'
import { BrandMark } from '@/components/brand-mark'
import { ThreadSidebar } from '@/components/chat/thread-sidebar'
import { Button } from '@/components/ui/button'
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

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

  useEffect(() => {
    if (!isSidebarOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsSidebarOpen(false)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isSidebarOpen])

  async function createThread() {
    setIsCreatingThread(true)
    setThreadsError(null)
    try {
      const thread = await api.chat.createThread()
      setThreads((current) => newestFirst([thread, ...current]))
      setIsSidebarOpen(false)
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

  function sidebar(onClose?: () => void) {
    return (
      <ThreadSidebar
        error={threadsError}
        isCreating={isCreatingThread}
        isLoading={isLoadingThreads}
        onClose={onClose}
        onCreate={() => void createThread()}
        onNavigate={() => setIsSidebarOpen(false)}
        onSignOut={() => void signOut()}
        threads={threads}
      />
    )
  }

  return (
    <main className="flex h-svh min-h-0 flex-col overflow-hidden bg-background md:grid md:grid-cols-[17.5rem_minmax(0,1fr)]">
      <header className="flex items-center gap-2 border-b bg-card px-3 py-2.5 md:hidden">
        <Button
          aria-controls="conversation-drawer"
          aria-expanded={isSidebarOpen}
          aria-label="Open conversations"
          onClick={() => setIsSidebarOpen(true)}
          size="icon"
          variant="ghost"
        >
          <Menu />
        </Button>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <BrandMark />
          <p className="truncate text-sm font-semibold tracking-tight">Document Copilot</p>
        </div>
        <Button
          aria-label="New conversation"
          disabled={isCreatingThread || isLoadingThreads}
          onClick={() => void createThread()}
          size="icon"
          variant="ghost"
        >
          <Plus />
        </Button>
      </header>

      <div className="hidden h-full min-h-0 md:block">{sidebar()}</div>

      {isSidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            aria-label="Close conversations"
            className="absolute inset-0 bg-ink/50"
            onClick={() => setIsSidebarOpen(false)}
            type="button"
          />
          <div
            className="relative h-full w-[min(20rem,88vw)] shadow-xl"
            id="conversation-drawer"
          >
            {sidebar(() => setIsSidebarOpen(false))}
          </div>
        </div>
      )}

      <section className="flex min-h-0 min-w-0 flex-1 flex-col bg-background">
        <Outlet context={outletContext} />
      </section>
    </main>
  )
}
