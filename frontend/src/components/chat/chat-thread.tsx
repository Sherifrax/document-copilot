import { useMemo, useState, type FormEvent } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { AlertCircle } from 'lucide-react'

import { ChatComposer } from '@/components/chat/chat-composer'
import { MessageList } from '@/components/chat/message-list'
import { Button } from '@/components/ui/button'
import { getAccessToken } from '@/lib/api'
import { env } from '@/lib/env'

type ChatThreadProps = {
  threadId: string
  title: string
  initialMessages: UIMessage[]
  onFinished: () => Promise<void>
}

export function ChatThread({
  threadId,
  title,
  initialMessages,
  onFinished,
}: ChatThreadProps) {
  const [input, setInput] = useState('')
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${env.apiBaseUrl}/chat/stream`,
        prepareSendMessagesRequest: async ({ messages, trigger, messageId }) => ({
          headers: { Authorization: `Bearer ${await getAccessToken()}` },
          body: { id: threadId, messages, trigger, messageId },
        }),
      }),
    [threadId],
  )
  const { messages, sendMessage, regenerate, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    onFinish: () => {
      void onFinished()
    },
  })
  const isStreaming = status === 'submitted' || status === 'streaming'
  const errorText = error?.message ?? ''
  const isAuthError = /401|unauthorized|expired|authentication/i.test(errorText)
  const isNetworkError = /failed to fetch|network|cors|load failed/i.test(errorText)
  const errorMessage = isAuthError
    ? 'Your session may have expired. Sign in again to continue.'
    : isNetworkError
      ? 'Could not reach the API. Check that the backend is running and the frontend API URL is correct.'
      : 'The filing search or grounded answer could not be completed. Please try again.'

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')
    void sendMessage({ text })
  }

  return (
    <div className="flex h-full min-h-[65svh] flex-col md:min-h-0">
      <header className="border-b px-5 py-4 md:px-8">
        <h1 className="truncate font-semibold">{title}</h1>
        <p className="mt-0.5 text-xs text-muted-foreground">SEC filing research · sourced answers</p>
      </header>
      <MessageList messages={messages} status={status} />
      <div className="border-t bg-background px-4 py-4 md:px-8">
        {error && (
          <div className="mx-auto mb-3 flex max-w-3xl items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm" role="alert">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
            <div className="min-w-0 flex-1">
              <p>{errorMessage}</p>
              {isAuthError ? (
                <a className="mt-1 inline-block font-medium underline underline-offset-4" href="/login">Sign in again</a>
              ) : (
                <p className="mt-1 text-xs text-muted-foreground">The current answer was not verified; don’t rely on it.</p>
              )}
            </div>
            {!isAuthError && (
              <Button onClick={() => void regenerate()} size="sm" variant="outline">Try again</Button>
            )}
          </div>
        )}
        <ChatComposer
          input={input}
          isStreaming={isStreaming}
          onInputChange={setInput}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  )
}
