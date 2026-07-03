"use client";

import type { Session, User } from "@supabase/supabase-js";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { setTokenProvider } from "@/lib/api/client";
import { getSupabaseClient } from "@/lib/supabase/client";

// Bound at module scope so the token provider exists before any child
// component's query can fire (child effects run before parent effects).
if (typeof window !== "undefined") {
  setTokenProvider(async () => {
    const { data } = await getSupabaseClient().auth.getSession();
    return data.session?.access_token ?? null;
  });
}

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  /** True until the initial session read resolves — gate redirects on this. */
  isLoading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const supabase = getSupabaseClient();

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setIsLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const value: AuthContextValue = {
    session,
    user: session?.user ?? null,
    isLoading,
    signOut: async () => {
      await getSupabaseClient().auth.signOut();
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }
  return ctx;
}
