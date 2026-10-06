import { useEffect, useRef, useState } from 'react'
import type { ChatStatus, UIMessage } from 'ai'
import { ExternalLink, FileText, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { STARTER_PROMPTS } from '@/lib/prompts'

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
  onAsk: (text: string) => void
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
    )
      return []
    return [citation as Citation]
  })
}

function citationLabel(citation: Citation) {
  const location = citation.pageNumber
    ? `p. ${citation.pageNumber}`
    : citation.section || 'filing section'
  return `${citation.ticker} ${citation.filingType} FY${citation.fiscalYear}, ${location}`
}

function isNoEvidence(text: string) {
  return /not enough evidence|could not find .*evidence|no relevant (filing )?evidence/i.test(text)
}

export function MessageList({ messages, status, onAsk }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const isStreaming = status === 'submitted' || status === 'streaming'

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: status === 'ready' ? 'smooth' : 'auto' })
  }, [messages, status])

  return (
    <div className="relative min-h-0 flex-1 overflow-y-auto" aria-live="polite">
      <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 py-6 sm:px-6 sm:py-8">
        {messages.length === 0 ? (
          <div className="my-auto max-w-xl py-8">
            <h2 className="font-serif text-2xl leading-tight tracking-tight sm:text-3xl">
              What should we pull from the filings?
            </h2>
            <p className="mt-3 max-w-[48ch] text-sm leading-6 text-muted-foreground">
              Ask about mix, margins, risk language, or capex. Every answer includes the passage
              it came from.
            </p>
            <ul className="mt-6 space-y-2">
              {STARTER_PROMPTS.map((prompt) => (
                <li key={prompt}>
                  <button
                    className="w-full rounded-md border bg-card px-3.5 py-3 text-left text-sm leading-6 transition-colors hover:border-ink/20 hover:bg-accent"
                    onClick={() => onAsk(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="space-y-8">
            {messages.map((message) => {
              const isUser = message.role === 'user'
              const text = messageText(message)
              const citations = isUser ? [] : messageCitations(message)
              if (!text) return null

              return (
                <article className="min-w-0" key={message.id}>
                  {isUser ? (
                    <div className="ml-auto max-w-[min(100%,40rem)] border-r-2 border-primary pr-4 text-right">
                      <p className="text-xs font-medium text-muted-foreground">You</p>
                      <p className="mt-1 text-sm leading-6">{text}</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">Copilot</p>
                      <p className="mt-2 font-serif text-[1.05rem] leading-7 whitespace-pre-wrap">
                        {text}
                      </p>
                      {isNoEvidence(text) && (
                        <div className="mt-3 rounded-md border border-amber-800/20 bg-amber-50 px-3 py-2 text-xs leading-5 text-foreground">
                          No supporting passage was found in the available filing corpus. Name a
                          company, filing, or fiscal year and try again.
                        </div>
                      )}
                      {citations.length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2" aria-label="Answer sources">
                          {citations.map((citation) => (
                            <button
                              aria-label={`Open source passage: ${citationLabel(citation)}`}
                              className="inline-flex max-w-full items-center gap-2 border border-t-[3px] border-t-cite bg-card px-2.5 py-1.5 text-left text-xs leading-5 transition-colors hover:bg-accent"
                              key={`${message.id}-${citation.index}-${citation.chunkId}`}
                              onClick={() => setSelectedCitation(citation)}
                              type="button"
                            >
                              <FileText className="size-3.5 shrink-0 text-cite" />
                              <span className="truncate">
                                {citation.ticker} {citation.filingType} FY{citation.fiscalYear}
                              </span>
                              <span className="shrink-0 text-muted-foreground">
                                {citation.pageNumber
                                  ? `p. ${citation.pageNumber}`
                                  : citation.section || 'section'}
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </article>
              )
            })}
            {isStreaming && (
              <div className="text-sm text-muted-foreground" role="status">
                <p className="text-xs font-medium">Copilot</p>
                <p className="mt-2">
                  {status === 'submitted' ? 'Searching filings…' : 'Writing a cited answer…'}
                </p>
              </div>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>
      {selectedCitation && (
        <div
          className="fixed inset-0 z-40 flex items-end bg-ink/40 md:items-stretch md:justify-end"
          role="presentation"
          onClick={() => setSelectedCitation(null)}
        >
          <aside
            aria-label="Source passage"
            aria-modal="true"
            className="max-h-[82svh] w-full overflow-y-auto rounded-t-lg border bg-card p-5 shadow-xl md:max-h-none md:w-[min(28rem,90vw)] md:rounded-none md:border-l md:border-t-0"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-serif text-xl leading-tight">{selectedCitation.companyName}</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {citationLabel(selectedCitation)}
                </p>
              </div>
              <Button
                aria-label="Close source passage"
                onClick={() => setSelectedCitation(null)}
                size="icon"
                variant="ghost"
              >
                <X />
              </Button>
            </div>
            <blockquote className="mt-6 border-l-2 border-cite pl-4 font-serif text-[0.98rem] leading-7 whitespace-pre-wrap">
              {selectedCitation.excerpt}
            </blockquote>
            <a
              className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-cite underline-offset-4 hover:underline"
              href={selectedCitation.sourceUrl}
              rel="noreferrer"
              target="_blank"
            >
              Open on EDGAR <ExternalLink className="size-4" />
            </a>
          </aside>
        </div>
      )}
    </div>
  )
}
