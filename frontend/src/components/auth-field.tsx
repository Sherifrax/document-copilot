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
        className="h-10 w-full rounded-lg border bg-background px-3 text-sm outline-none transition focus:border-ring focus:ring-3 focus:ring-ring/20"
      />
    </label>
  )
}
