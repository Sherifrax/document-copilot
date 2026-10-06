import type { FormEvent, KeyboardEvent } from 'react'
import { ArrowUp } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

type ChatComposerProps = {
  input: string
  isStreaming: boolean
  onInputChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function ChatComposer({
  input,
  isStreaming,
  onInputChange,
  onSubmit,
}: ChatComposerProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <form className="mx-auto flex max-w-3xl items-end gap-2" onSubmit={onSubmit}>
      <Textarea
        aria-label="Question"
        className="max-h-40 min-h-12 resize-none py-3"
        disabled={isStreaming}
        onChange={(event) => onInputChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about a company, filing, or year"
        rows={1}
        value={input}
      />
      <Button
        aria-label="Send question"
        className="size-12 shrink-0"
        disabled={isStreaming || input.trim() === ''}
        size="icon-lg"
        type="submit"
      >
        <ArrowUp />
      </Button>
    </form>
  )
}
