import { useEffect, useRef, useState } from 'react'
import type { ChatStatus, UIMessage } from 'ai'
import { Bot, ExternalLink, FileText, UserRound, X } from 'lucide-react'

import { Button } from '@/components/ui/button'

type Citation = {
  index: number
  chunkId: string
  ticker: string
  companyName: string
  filingType: string
  fiscalYear: number
  pageNumber: number | null
  section: string | null
  sourceUrl: string
  excerpt: string
}

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

function messageCitations(message: UIMessage): Citation[] {
  return message.parts.flatMap((part) => {
    if (part.type !== 'data-citation' || !('data' in part)) return []
    const data: unknown = part.data
    if (!data || typeof data !== 'object') return []
    const citation = data as Partial<Citation>
    if (
      typeof citation.index !== 'number' ||
      typeof citation.ticker !== 'string' ||
      typeof citation.companyName !== 'string' ||
      typeof citation.filingType !== 'string' ||
      typeof citation.fiscalYear !== 'number' ||
      typeof citation.excerpt !== 'string' ||
      typeof citation.sourceUrl !== 'string'
    ) return []
    return [citation as Citation]
  })
}

function citationLabel(citation: Citation) {
  const location = citation.pageNumber
    ? `p. ${citation.pageNumber}`
    : citation.section || 'filing section'
  return `${citation.ticker} · ${citation.filingType} · FY ${citation.fiscalYear} · ${location}`
}

function isNoEvidence(text: string) {
  return /not enough evidence|could not find .*evidence|no relevant (filing )?evidence/i.test(text)
}

export function MessageList({ messages, status }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const isStreaming = status === 'submitted' || status === 'streaming'

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: status === 'ready' ? 'smooth' : 'auto' })
  }, [messages, status])

  return (
    <div className="relative min-h-0 flex-1 overflow-y-auto" aria-live="polite">
      <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 py-8 md:px-6">
        {messages.length === 0 ? (
          <div className="my-auto py-16 text-center">
            <span className="mx-auto grid size-11 place-items-center rounded-2xl bg-muted">
              <Bot className="size-5" />
            </span>
            <h2 className="mt-4 text-lg font-semibold">What would you like to investigate?</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ask a question about the SEC filings. Answers include source passages you can verify.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((message) => {
              const isUser = message.role === 'user'
              const text = messageText(message)
              const citations = isUser ? [] : messageCitations(message)
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
                  <div className="max-w-[85%]">
                    <div
                      className={`whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
                        isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
                      }`}
                    >
                      {text}
                    </div>
                    {!isUser && isNoEvidence(text) && (
                      <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-muted-foreground">
                        No supporting passage was found in the available filing corpus. Try naming a company, filing, or fiscal year.
                      </div>
                    )}
                    {citations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2" aria-label="Answer sources">
                        {citations.map((citation) => (
                          <button
                            aria-label={`Open source passage: ${citationLabel(citation)}`}
                            className="inline-flex max-w-full items-center gap-1.5 rounded-full border bg-background px-3 py-1.5 text-left text-xs text-foreground transition-colors hover:bg-accent"
                            key={`${message.id}-${citation.index}-${citation.chunkId}`}
                            onClick={() => setSelectedCitation(citation)}
                            type="button"
                          >
                            <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                            <span className="truncate">{citation.companyName} · {citation.filingType} · FY {citation.fiscalYear}</span>
                            <span className="shrink-0 text-muted-foreground">{citation.pageNumber ? `p. ${citation.pageNumber}` : citation.section || 'section'}</span>
                          </button>
                        ))}
                      </div>
                    )}
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
              <div className="flex items-center gap-3 text-sm text-muted-foreground" role="status">
                <span className="grid size-8 place-items-center rounded-full bg-primary text-primary-foreground">
                  <Bot className="size-4" />
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-1.5 animate-pulse rounded-full bg-current" />
                  {status === 'submitted' ? 'Searching filings…' : 'Writing a cited answer…'}
                </span>
              </div>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>
      {selectedCitation && (
        <div className="fixed inset-0 z-40 flex items-end bg-black/30 md:items-stretch md:justify-end" role="presentation" onClick={() => setSelectedCitation(null)}>
          <aside
            aria-label="Source passage"
            aria-modal="true"
            className="max-h-[80svh] w-full overflow-y-auto rounded-t-2xl border bg-background p-5 shadow-xl md:max-h-none md:w-[min(32rem,90vw)] md:rounded-none md:border-l md:border-t-0"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Source passage</p>
                <h2 className="mt-1 text-lg font-semibold">{selectedCitation.companyName}</h2>
              </div>
              <Button aria-label="Close source passage" onClick={() => setSelectedCitation(null)} size="icon" variant="ghost">
                <X />
              </Button>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">{citationLabel(selectedCitation)}</p>
            <blockquote className="mt-5 whitespace-pre-wrap border-l-2 border-primary pl-4 text-sm leading-6">
              {selectedCitation.excerpt}
            </blockquote>
            <a
              className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary underline-offset-4 hover:underline"
              href={selectedCitation.sourceUrl}
              rel="noreferrer"
              target="_blank"
            >
              Open original filing <ExternalLink className="size-4" />
            </a>
          </aside>
        </div>
      )}
    </div>
  )
}
