"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Session, User, AuthChangeEvent } from '@supabase/supabase-js';

type AuthContextType = {
  user: User | null;
  isAdmin: boolean;
  loading: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const supabase = createClient();
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkUser = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const currentUser = session?.user ?? null;
      setUser(currentUser);

      let adminStatus = false;
      if (currentUser) {
        const { data, error } = await supabase.rpc('is_admin');
        if (error) {
          console.error('Error checking admin status:', error);
        } else {
          adminStatus = data;
        }
      }
      setIsAdmin(adminStatus);
      setLoading(false);
    };

    checkUser();

    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        const currentUser = session?.user ?? null;
        setUser(currentUser);

        let adminStatus = false;
        if (currentUser) {
          const { data, error } = await supabase.rpc('is_admin');
          if (error) {
            console.error('Error checking admin status:', error);
          } else {
            adminStatus = data;
          }
        }
        setIsAdmin(adminStatus);
        setLoading(false);

        if (event === 'SIGNED_IN') {
          if (adminStatus) {
            router.push('/enterprise/admin/dashboard');
          } else {
            router.push('/dashboard');
          }
        } else if (event === 'SIGNED_OUT') {
          router.push('/login');
        }
      }
    );

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [supabase, router]);

  const value = { user, isAdmin, loading };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};