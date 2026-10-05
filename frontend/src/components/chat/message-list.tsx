import { useEffect, useRef } from 'react'
import type { ChatStatus, UIMessage } from 'ai'
import { Bot, UserRound } from 'lucide-react'

type MessageListProps = {
  messages: UIMessage[]
  status: ChatStatus
}

function messageText(message: UIMessage) {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
}

export function MessageList({ messages, status }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const isStreaming = status === 'submitted' || status === 'streaming'

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: status === 'ready' ? 'smooth' : 'auto' })
  }, [messages, status])

  return (
    <div className="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
      <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 py-8 md:px-6">
        {messages.length === 0 ? (
          <div className="my-auto py-16 text-center">
            <span className="mx-auto grid size-11 place-items-center rounded-2xl bg-muted">
              <Bot className="size-5" />
            </span>
            <h2 className="mt-4 text-lg font-semibold">What would you like to investigate?</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Send a message to test the authenticated streaming path.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((message) => {
              const isUser = message.role === 'user'
              const text = messageText(message)
              if (!text) return null

              return (
                <article
                  className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                  key={message.id}
                >
                  {!isUser && (
                    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground">
                      <Bot className="size-4" />
                    </span>
                  )}
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
                      isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    }`}
                  >
                    {text}
                  </div>
                  {isUser && (
                    <span className="grid size-8 shrink-0 place-items-center rounded-full border bg-background">
                      <UserRound className="size-4" />
                    </span>
                  )}
                </article>
              )
            })}
            {isStreaming && (
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <span className="grid size-8 place-items-center rounded-full bg-primary text-primary-foreground">
                  <Bot className="size-4" />
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-1.5 animate-pulse rounded-full bg-current" />
                  Assistant is responding…
                </span>
              </div>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  )
}
