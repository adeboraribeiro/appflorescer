import AsyncStorage from '@react-native-async-storage/async-storage'
import { createClient } from '@supabase/supabase-js'
import 'react-native-url-polyfill/auto'

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY

// Do NOT throw at module load time; in production builds some env vars may be
// unavailable at import time. Create the client only when the variables exist.
let _supabase: any = null
if (supabaseUrl && supabaseAnonKey) {
  _supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      storage: AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  })
} else {
  // Log a warning so developers can detect misconfiguration without crashing the app
  // (avoid throwing here — throwing during module import causes a white screen in production)
  // The rest of the app should handle a missing client gracefully.
  // eslint-disable-next-line no-console
  console.warn('app/lib/supabase: EXPO_PUBLIC_SUPABASE_URL or EXPO_PUBLIC_SUPABASE_ANON_KEY is missing; Supabase client not created.')
}

export const supabase = _supabase

// Test connection
export async function testSupabaseConnection() {
  try {
  const { data, error } = await supabase.from('profiles').select('id').limit(1)
    if (error) throw error
    console.log('Supabase connection successful!')
    return true
  } catch (error) {
    console.error('Supabase connection failed:', error instanceof Error ? error.message : 'Unknown error')
    return false
  }
}

// Default export to satisfy Expo Router when scanning files under app/
// Default export of a dummy component to prevent Expo Router from treating this file as a route
export default function SupabaseRouteShim() { return null }