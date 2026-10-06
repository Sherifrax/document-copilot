import { MessageSquareText } from 'lucide-react'
import { useOutletContext } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import type { ChatLayoutContext } from '@/lib/chat'

export function ChatListPage() {
  const { threads, isLoadingThreads, isCreatingThread, createThread } =
    useOutletContext<ChatLayoutContext>()

  return (
    <div className="grid h-full place-items-center px-5 py-12 sm:px-8">
      <div className="max-w-lg">
        <p className="font-serif text-3xl leading-tight tracking-tight sm:text-4xl">
          {threads.length === 0 ? 'Start with a filing question' : 'Open a conversation'}
        </p>
        <p className="mt-3 max-w-[42ch] text-sm leading-6 text-muted-foreground">
          {threads.length === 0
            ? 'Ask in plain English. Answers cite the company, filing, year, and page so you can check the source.'
            : 'Pick a thread from the sidebar, or start a new one for a different line of inquiry.'}
        </p>
        <Button
          className="mt-7"
          disabled={isLoadingThreads || isCreatingThread}
          onClick={() => void createThread()}
          size="lg"
        >
          <MessageSquareText data-icon="inline-start" />
          {isCreatingThread ? 'Creating…' : 'New conversation'}
        </Button>
      </div>
    </div>
  )
}
