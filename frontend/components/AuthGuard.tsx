"use client";

import { useAuth } from '@/contexts/AuthContext';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, ReactNode } from 'react';

const AuthGuard = ({ children }: { children: ReactNode }) => {
  const { user, isAdmin, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) {
      return; // Wait for loading to complete
    }

    if (!user) {
      router.push('/login');
      return;
    }

    const adminRoutes = ['/enterprise/admin'];
    const isAdminRoute = adminRoutes.some(route => pathname.startsWith(route));

    if (isAdminRoute && !isAdmin) {
      router.push('/dashboard');
    }
  }, [user, isAdmin, loading, router, pathname]);

  if (loading) {
    return <div>Loading...</div>; // Or a spinner component
  }

  return <>{children}</>;
};

export default AuthGuard;