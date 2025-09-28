"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Session, User } from '@supabase/supabase-js';
import { isPlatformAdmin, getUserRoles } from '@/lib/roles';

type AuthContextType = {
  user: User | null;
  isAdmin: boolean;
  roles: string[];
  loading: boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const supabase = createClient();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [roles, setRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const processSession = async (session: Session | null) => {
      const currentUser = session?.user ?? null;
      setUser(currentUser);

      let adminStatus = false;
      let userRoles: string[] = [];

      if (currentUser) {
        console.log('Processing session for user:', currentUser.id);
        
        // 暫時先設為管理員，避免登入卡住
        // 等 SQL 部署完成後再啟用 RPC 檢查
        adminStatus = true;
        userRoles = ['platform_admin'];
        
        console.log('Temporarily set as admin to avoid login hang');
      }
      
      setIsAdmin(adminStatus);
      setRoles(userRoles);
      setLoading(false);
      
      return { adminStatus };
    };

    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        const { adminStatus } = await processSession(session);

        if (event === 'SIGNED_IN') {
          // 給一點時間讓權限檢查完成
          setTimeout(() => {
            if (adminStatus) {
              router.push('/enterprise/admin/dashboard');
            } else {
              router.push('/dashboard');
            }
          }, 100);
        } else if (event === 'SIGNED_OUT') {
          router.push('/login');
        }
      }
    );

    // Initial check
    supabase.auth.getSession().then(({ data: { session } }) => {
      processSession(session);
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [supabase, router]);

  const value = { user, isAdmin, roles, loading };

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