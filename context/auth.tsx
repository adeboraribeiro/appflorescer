import { Session } from '@supabase/supabase-js';
import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

type AuthContextType = {
  user: Session['user'] | null;
  loading: boolean;
  setUser: (user: Session['user'] | null) => void;
  signIn: (emailOrUsername: string, password: string) => Promise<Session['user'] | null>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  setUser: () => {},
  signIn: async () => null,
  signOut: async () => {},
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<Session['user'] | null>(null);
  const [loading, setLoading] = useState(true);

  const signIn = async (emailOrUsername: string, password: string) => {
    try {
      // First try with email
      const { data: { user }, error } = await supabase.auth.signInWithPassword({
        email: emailOrUsername,
        password,
      });

      if (error && emailOrUsername.indexOf('@') === -1) {
        // If login fails and input doesn't look like an email, try to find the user by username
        const { data: profiles } = await supabase
          .from('profiles')
          .select('email')
          .eq('username', emailOrUsername)
          .single();

        if (profiles?.email) {
          // Try login again with the found email
          const { data: { user: userByUsername }, error: loginError } = await supabase.auth.signInWithPassword({
            email: profiles.email,
            password,
          });

          if (loginError) throw loginError;
          return userByUsername;
        }
      }

      if (error) throw error;
      return user;
    } catch (error) {
      console.error('Error signing in:', error);
      throw error;
    }
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  useEffect(() => {
    // Check active sessions and sets the user
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for changes on auth state
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};