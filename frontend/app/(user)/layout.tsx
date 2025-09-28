"use client";

import AuthGuard from '@/components/AuthGuard';
import { ReactNode } from 'react';

import UserDashboardLayout from '@/components/UserDashboardLayout';

const UserLayout = ({ children }: { children: ReactNode }) => {
  return (
    <AuthGuard>
      <UserDashboardLayout>{children}</UserDashboardLayout>
    </AuthGuard>
  );
};

export default UserLayout;