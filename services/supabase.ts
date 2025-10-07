import { createClient } from '@supabase/supabase-js';
import Constants from 'expo-constants';
import 'react-native-url-polyfill/auto';

const supabaseUrl = Constants.expoConfig?.extra?.supabaseUrl;
const supabaseAnonKey = Constants.expoConfig?.extra?.supabaseAnonKey;

let _supabase: any = null;
if (supabaseUrl && supabaseAnonKey) {
  _supabase = createClient(supabaseUrl, supabaseAnonKey);
} else {
  // Avoid throwing during module import; Expo Router may scan files under app/ and
  // cause this file to be evaluated even when env vars are not available. Log a warning.
  // eslint-disable-next-line no-console
  console.warn('services/supabase: supabaseUrl or supabaseAnonKey missing; client not created.');
}

export const supabase = _supabase;

// Add default export
export default supabase;