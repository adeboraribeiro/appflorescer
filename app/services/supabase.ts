export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          created_at?: string
          updated_at?: string
          username: string
          email: string
          first_name: string
          last_name: string
          birth_date: string
          avatar_url?: string
          role: string
          // persisted user preferences and onboarding state
          applanguage?: string | null
          apptheme?: string | null
          // selectedmodules stored as an array of numeric ids
          selectedmodules?: number[] | null
          onboarding_completed?: boolean | null
        }
        Insert: {
          id?: string
          created_at?: string
          updated_at?: string
          username: string
          email: string
          first_name: string
          last_name: string
          birth_date: string
          avatar_url?: string
          role?: string
          applanguage?: string | null
          apptheme?: string | null
          selectedmodules?: number[] | null
          onboarding_completed?: boolean | null
        }
        Update: {
          id?: string
          created_at?: string
          updated_at?: string
          username?: string
          email?: string
          first_name?: string
          last_name?: string
          birth_date?: string
          avatar_url?: string
          role?: string
          applanguage?: string | null
          apptheme?: string | null
          selectedmodules?: number[] | null
          onboarding_completed?: boolean | null
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}
