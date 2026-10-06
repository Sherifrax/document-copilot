import { cn } from '@/lib/utils'

type BrandMarkProps = {
  className?: string
  inverted?: boolean
}

export function BrandMark({ className, inverted = false }: BrandMarkProps) {
  return (
    <img
      src="/logo.png"
      alt=""
      aria-hidden="true"
      className={cn(
        'size-8 shrink-0 object-contain',
        inverted ? 'brightness-105' : undefined,
        className,
      )}
    />
  )
}
