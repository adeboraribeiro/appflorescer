import { create } from 'zustand';
import { supabase } from '../lib/supabase';
// The repo does not currently expose a central `types/supabase` file.
// Use lightweight local aliases for now to keep the store typed without
// introducing a hard dependency. These can be replaced with proper
// typed interfaces later.
type Profile = any;
type UserSettings = any;

type SettingsStore = {
  profile: Profile | null;
  userSettings: UserSettings | null;
  loading: boolean;
  error: string | null;
  fetchProfile: (userId: string) => Promise<void>;
  fetchUserSettings: (userId: string) => Promise<void>;
  updateProfile: (userId: string, updates: Partial<Profile>) => Promise<void>;
  updateUserSettings: (userId: string, updates: Partial<UserSettings>) => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  profile: null,
  userSettings: null,
  loading: false,
  error: null,

  fetchProfile: async (userId: string) => {
    try {
      set({ loading: true, error: null });
      const { data, error } = await supabase
        .from('profiles')
        .select('id, first_name, last_name, username, birth_date, profile_image, applanguage, apptheme, selectedmodules, onboarding_completed, updated_at')
        .eq('id', userId)
        .single();

      if (error) throw error;
      set({ profile: data, loading: false });
    } catch (error) {
      set({ error: (error as Error).message, loading: false });
    }
  },

  fetchUserSettings: async (userId: string) => {
    try {
      set({ loading: true, error: null });
      const { data, error } = await supabase
        .from('user_settings')
        .select('*')
        .eq('user_id', userId)
        .single();

      if (error) throw error;
      set({ userSettings: data, loading: false });
    } catch (error) {
      set({ error: (error as Error).message, loading: false });
    }
  },

  updateProfile: async (userId: string, updates: Partial<Profile>) => {
    try {
      set({ loading: true, error: null });
      const { data, error } = await supabase
        .from('profiles')
        .update(updates)
        .eq('id', userId)
        .select('id, first_name, last_name, username, birth_date, profile_image, applanguage, apptheme, selectedmodules, onboarding_completed, updated_at')
        .single();

      if (error) throw error;
      set({ profile: data, loading: false });
    } catch (error) {
      set({ error: (error as Error).message, loading: false });
    }
  },

  updateUserSettings: async (userId: string, updates: Partial<UserSettings>) => {
    try {
      set({ loading: true, error: null });
      const { data, error } = await supabase
        .from('user_settings')
        .update(updates)
        .eq('user_id', userId)
        .select()
        .single();

      if (error) throw error;
      set({ userSettings: data, loading: false });
    } catch (error) {
      set({ error: (error as Error).message, loading: false });
    }
  }
}));
