import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import type { DashboardAppConfig } from '@/shared/lib/types'

let cachedClient: SupabaseClient | null = null
let cachedSignature = ''

export function getBrowserSupabaseClient(
  config: DashboardAppConfig,
): SupabaseClient {
  const signature = `${config.supabase_url}::${config.supabase_publishable_key}`
  if (cachedClient && cachedSignature === signature) {
    return cachedClient
  }

  cachedClient = createClient(
    config.supabase_url,
    config.supabase_publishable_key,
    {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        flowType: 'implicit',
      },
    },
  )
  cachedSignature = signature
  return cachedClient
}
