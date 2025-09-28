"use client";

import AuthGuard from '@/components/AuthGuard';
import { ReactNode } from 'react';

import AdminDashboardLayout from '@/components/AdminDashboardLayout';

const AdminLayout = ({ children }: { children: ReactNode }) => {
  return (
    <AuthGuard>
      <AdminDashboardLayout>{children}</AdminDashboardLayout>
    </AuthGuard>
  );
};

export default AdminLayout;