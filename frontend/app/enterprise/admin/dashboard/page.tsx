"use client";

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

export default function AdminDashboardPage() {
  const { user } = useAuth();

  return (
    <div className="p-4 md:p-8">
      <h1 className="text-2xl font-bold mb-4">管理後台儀表板</h1>
      <p className="mb-8">
        歡迎回來, {user?.email}!
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Members Management Card */}
        <Link href="/admin/dashboard/members" className="block p-6 bg-white border border-gray-200 rounded-lg shadow hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700">
          <h5 className="mb-2 text-xl font-bold tracking-tight text-gray-900 dark:text-white">會員管理</h5>
          <p className="font-normal text-gray-700 dark:text-gray-400">查看、新增、編輯系統中的所有使用者。</p>
        </Link>
        
        {/* Enterprises Management Card */}
        <Link href="/admin/dashboard/enterprises" className="block p-6 bg-white border border-gray-200 rounded-lg shadow hover:bg-gray-100 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700">
          <h5 className="mb-2 text-xl font-bold tracking-tight text-gray-900 dark:text-white">企業管理</h5>
          <p className="font-normal text-gray-700 dark:text-gray-400">管理企業帳戶與其對應的企業卡。</p>
        </Link>
      </div>
    </div>
  );
}