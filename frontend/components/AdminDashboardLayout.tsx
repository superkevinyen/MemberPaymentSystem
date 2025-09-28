"use client";

import Link from 'next/link';
import { ReactNode } from 'react';

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const AdminDashboardLayout = ({ children }: { children: ReactNode }) => {
  return (
    <div className="flex min-h-screen bg-gray-100">
      <aside className="w-64 bg-white border-r">
        <div className="p-4">
          <h1 className="text-2xl font-bold">Admin</h1>
        </div>
        <nav className="p-4">
          <ul>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start">
                <Link href="/enterprise/admin/dashboard">Dashboard</Link>
              </Button>
            </li>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start">
                <Link href="/enterprise/admin/dashboard/members">Members</Link>
              </Button>
            </li>
            <li className="mb-2">
              <Button asChild variant="ghost" className="w-full justify-start">
                <Link href="/enterprise/admin/dashboard/enterprises">Enterprises</Link>
              </Button>
            </li>
          </ul>
        </nav>
      </aside>
      <main className="flex-1 p-4">
        <Card>
          <CardContent>
            {children}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default AdminDashboardLayout;