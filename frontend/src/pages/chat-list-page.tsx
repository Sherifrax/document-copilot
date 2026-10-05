import { MessageSquareText } from 'lucide-react'
import { useOutletContext } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import type { ChatLayoutContext } from '@/lib/chat'

export function ChatListPage() {
  const { threads, isLoadingThreads, isCreatingThread, createThread } =
    useOutletContext<ChatLayoutContext>()

  return (
    <div className="grid h-full min-h-[65svh] place-items-center px-6 py-16 md:min-h-0">
      <div className="max-w-md text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-muted">
          <MessageSquareText className="size-5" />
        </span>
        <h1 className="mt-5 text-2xl font-semibold tracking-tight">
          {threads.length === 0 ? 'Start your first conversation' : 'Choose a conversation'}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {threads.length === 0
            ? 'Create a thread to ask questions about the filing corpus.'
            : 'Open a previous conversation from the sidebar, or start a new one.'}
        </p>
        <Button
          className="mt-6"
          disabled={isLoadingThreads || isCreatingThread}
          onClick={() => void createThread()}
        >
          {isCreatingThread ? 'Creating…' : 'New conversation'}
        </Button>
      </div>
    </div>
  )
}
