type Environment = {
  apiBaseUrl: string
  supabaseUrl: string
  supabaseAnonKey: string
}

function required(name: keyof ImportMetaEnv): string {
  const value = import.meta.env[name]
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return value.replace(/\/$/, '')
}

export const env: Environment = {
  apiBaseUrl: required('VITE_API_BASE_URL'),
  supabaseUrl: required('VITE_SUPABASE_URL'),
  supabaseAnonKey: required('VITE_SUPABASE_ANON_KEY'),
}
