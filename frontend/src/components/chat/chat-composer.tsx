import type { FormEvent, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

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
        aria-label="Message"
        className="max-h-40 min-h-11 resize-none py-2.5"
        disabled={isStreaming}
        onChange={(event) => onInputChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about the filing corpus…"
        rows={1}
        value={input}
      />
      <Button
        aria-label="Send message"
        className="size-11"
        disabled={isStreaming || input.trim() === ''}
        size="icon-lg"
        type="submit"
      >
        <Send />
      </Button>
    </form>
  )
}
