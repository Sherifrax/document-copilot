import { useEffect, useState } from 'react'
import type { UIMessage } from 'ai'
import { Link, useOutletContext, useParams } from 'react-router-dom'

import { ChatThread } from '@/components/chat/chat-thread'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { ChatLayoutContext } from '@/lib/chat'

export function ChatThreadPage() {
  const { threadId } = useParams()
  const { threads, refreshThreads } = useOutletContext<ChatLayoutContext>()
  const [loadState, setLoadState] = useState<{
    threadId: string
    messages: UIMessage[] | null
    error: string | null
  } | null>(null)

  useEffect(() => {
    if (!threadId) return

    let isCurrent = true

    void api.chat
      .getMessages(threadId)
      .then((storedMessages) => {
        if (isCurrent) {
          setLoadState({ threadId, messages: storedMessages, error: null })
        }
      })
      .catch((requestError: unknown) => {
        if (isCurrent) {
          setLoadState({
            threadId,
            messages: null,
            error:
              requestError instanceof Error ? requestError.message : 'Unable to load conversation',
          })
        }
      })

    return () => {
      isCurrent = false
    }
  }, [threadId])

  if (!threadId) return null

  const currentState = loadState?.threadId === threadId ? loadState : null

  if (currentState?.error) {
    return (
      <div className="grid h-full min-h-[65svh] place-items-center px-6 text-center md:min-h-0">
        <div>
          <h1 className="text-xl font-semibold">Conversation unavailable</h1>
          <p className="mt-2 text-sm text-destructive">{currentState.error}</p>
          <Button asChild className="mt-5" variant="outline">
            <Link to="/chat">Back to conversations</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (currentState?.messages == null) {
    return (
      <div className="grid h-full min-h-[65svh] place-items-center text-sm text-muted-foreground md:min-h-0">
        Loading conversation…
      </div>
    )
  }

  const thread = threads.find((candidate) => candidate.id === threadId)

  return (
    <ChatThread
      key={threadId}
      threadId={threadId}
      title={thread?.title ?? 'Conversation'}
      initialMessages={currentState.messages}
      onFinished={refreshThreads}
    />
  )
}
