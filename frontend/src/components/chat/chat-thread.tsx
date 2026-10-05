import { useMemo, useState, type FormEvent } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { ChatComposer } from '@/components/chat/chat-composer'
import { MessageList } from '@/components/chat/message-list'
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
  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    onFinish: () => {
      void onFinished()
    },
  })
  const isStreaming = status === 'submitted' || status === 'streaming'

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
        <p className="mt-0.5 text-xs text-muted-foreground">Stubbed assistant stream</p>
      </header>
      <MessageList messages={messages} status={status} />
      <div className="border-t bg-background px-4 py-4 md:px-8">
        {error && (
          <p className="mx-auto mb-3 max-w-3xl text-sm text-destructive" role="alert">
            {error.message}
          </p>
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
