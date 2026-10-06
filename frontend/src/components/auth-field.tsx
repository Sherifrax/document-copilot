type AuthFieldProps = {
  label: string
  name: string
  type: 'email' | 'password'
  autoComplete: string
}

export function AuthField({ label, ...props }: AuthFieldProps) {
  return (
    <label className="block space-y-2 text-left text-sm font-medium">
      <span>{label}</span>
      <input
        {...props}
        required
        className="h-11 w-full rounded-md border bg-card px-3 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20"
      />
    </label>
  )
}
