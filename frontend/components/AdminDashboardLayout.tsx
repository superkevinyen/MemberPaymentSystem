"use client";

import Link from 'next/link';
import { ReactNode } from 'react';

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const AdminDashboardLayout = ({ children }: { children: ReactNode }) => {
  return (
    <div className="flex min-h-screen bg-gray-900">
      <aside className="w-64 bg-gray-800 border-r border-gray-700">
        <div className="p-4">
          <h1 className="text-2xl font-bold text-white">Admin</h1>
        </div>
        <nav className="p-4">
          <ul>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start text-gray-300 hover:text-white hover:bg-gray-700">
                <Link href="/enterprise/admin/dashboard">Dashboard</Link>
              </Button>
            </li>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start text-gray-300 hover:text-white hover:bg-gray-700">
                <Link href="/enterprise/admin/dashboard/members">Members</Link>
              </Button>
            </li>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start text-gray-300 hover:text-white hover:bg-gray-700">
                <Link href="/enterprise/admin/dashboard/enterprises">Enterprises</Link>
              </Button>
            </li>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start text-gray-300 hover:text-white hover:bg-gray-700">
                <Link href="/enterprise/admin/dashboard/transactions">Transactions</Link>
              </Button>
            </li>
          </ul>
        </nav>
      </aside>
      <main className="flex-1 p-4">
        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="text-white">
            {children}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default AdminDashboardLayout;