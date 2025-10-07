import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';
import 'react-native-url-polyfill/auto';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

// allow reassigning the client when reconnecting
// Export as `any` to keep this module resilient when env vars are missing
export let supabase: any = null;

// guard to avoid recreating the client too often (prevents auth refresh storms)
let _lastReconnectAt = 0;
const MIN_RECONNECT_INTERVAL_MS = 30_000; // 30s

function createRealClient() {
  return createClient(supabaseUrl!, supabaseAnonKey!, {
    auth: {
      storage: AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  });
}

// If environment variables are present, create a real Supabase client.
// Otherwise, provide a safe no-op fallback client that doesn't throw during import.
if (supabaseUrl && supabaseAnonKey) {
  try {
    supabase = createRealClient();
  } catch (e) {
    // If client creation fails, fall back to a no-op client rather than throwing
    // to avoid crashing the app at startup.
    // eslint-disable-next-line no-console
    console.warn('supabase: failed to create real client, falling back to noop client', e);
  }
}

if (!supabase) {
  // Minimal no-op supabase client to avoid synchronous throws on import.
  // Methods return benign shapes expected by the codebase or simple no-ops.
  const noopAsync = async () => ({ data: null, error: null });
  const noopAuth = {
    getSession: async () => ({ data: { session: null } }),
    getUser: async () => ({ data: { user: null } }),
    onAuthStateChange: (_cb: any) => ({ data: { subscription: { unsubscribe: () => {} } } }),
    signInWithPassword: async () => ({ data: null, error: new Error('supabase not configured') }),
    signUp: async () => ({ data: null, error: new Error('supabase not configured') }),
    signOut: async () => ({ error: null }),
  };

  const noopFromBuilder = () => {
    const builder: any = {
      select: async () => ({ data: null, error: new Error('supabase not configured') }),
      maybeSingle: async () => ({ data: null, error: new Error('supabase not configured') }),
      single: async () => ({ data: null, error: new Error('supabase not configured') }),
      eq: function () { return this; },
    };
    return builder;
  };

  supabase = {
    auth: noopAuth,
    from: (_: string) => noopFromBuilder(),
    rpc: async () => ({ data: null, error: new Error('supabase not configured') }),
    // allow reconnect logic to attempt creating a real client later
  };
}

export function reconnectSupabase() {
  const now = Date.now();
  if (now - _lastReconnectAt < MIN_RECONNECT_INTERVAL_MS) {
    // eslint-disable-next-line no-console
    console.warn('reconnectSupabase: skipped (rate-limited)');
    return false;
  }
  _lastReconnectAt = now;

  if (!supabaseUrl || !supabaseAnonKey) {
    // eslint-disable-next-line no-console
    console.warn('reconnectSupabase: supabase env vars missing; cannot recreate client');
    return false;
  }

  try {
    // eslint-disable-next-line no-console
    console.log('reconnectSupabase: recreating Supabase client');
    supabase = createRealClient();
    return true;
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('reconnectSupabase: failed to recreate client', e);
    return false;
  }
}

// Test connection
export async function testSupabaseConnection() {
  try {
    // First, ensure the auth layer responds. This avoids attempting row-level
    // protected selects before a session is established which cause RLS errors.
    try {
      const { data: { session } } = await supabase.auth.getSession();
      // If we have a session object the client/auth subsystem is healthy.
      if (session) {
        console.log('Supabase auth session present')
        return true
      }
    } catch (e) {
      // ignore - we'll fall back to a lightweight REST probe below
    }

    // Fallback: perform a lightweight REST probe to the Supabase REST root.
    // We don't issue any protected selects here; this request simply checks
    // that the Supabase HTTP endpoint is reachable and responding.
    const probeUrl = `${supabaseUrl}/rest/v1/`;
    try {
      const res = await fetch(probeUrl, {
        method: 'GET',
        headers: {
          apikey: supabaseAnonKey || '',
          Authorization: `Bearer ${supabaseAnonKey || ''}`,
        },
      });
      // If we get any HTTP response, the server is reachable. Treat network
      // or auth errors as "reachable" so reconnect logic doesn't spam when
      // the SDK hasn't established a session yet.
      if (res) {
        console.log('Supabase REST endpoint reachable (status:', res.status, ')')
        return true
      }
    } catch (fetchErr) {
      console.error('Supabase REST probe failed:', fetchErr instanceof Error ? fetchErr.message : String(fetchErr));
      return false
    }

    // If we fell through, report failure.
    console.error('Supabase connection failed: unknown state')
    return false
  } catch (error) {
    console.error('Supabase connection failed:', error instanceof Error ? error.message : 'Unknown error')
    return false
  }
}

// Ensure the supabase client is connected; try reconnecting once if test fails
export async function ensureSupabaseConnected(retries = 3, delayMs = 1000) {
  for (let attempt = 0; attempt < retries; attempt++) {
    const ok = await testSupabaseConnection()
    if (ok) return true
    console.warn(`Supabase not reachable (attempt ${attempt + 1}/${retries}), reconnecting...`)
    reconnectSupabase()
    // wait before next attempt
    await new Promise(resolve => setTimeout(resolve, delayMs * (attempt + 1)))
  }
  return false
}

export default supabase