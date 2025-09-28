"use client";

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import { toast } from 'react-hot-toast';

// Define the type for our user data based on the RPC return type
type User = {
  id: string;
  email: string | null;
  name: string | null;
  is_admin: boolean | null;
  created_at: string | null;
};

export default function MembersPage() {
  const supabase = createClient();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchUsers() {
    setLoading(true);
    const { data, error } = await supabase.rpc('get_all_users_for_admin');
    if (error) {
      toast.error('讀取使用者列表失敗: ' + error.message);
      console.error(error);
    } else {
      setUsers(data || []);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleAdmin = async (user_id: string, current_is_admin: boolean | null) => {
    const newAdminStatus = !current_is_admin;
    const { error } = await supabase.rpc('admin_update_user_metadata', {
      p_user_id: user_id,
      p_metadata: { is_admin: newAdminStatus }
    });

    if (error) {
      toast.error('更新管理員狀態失敗: ' + error.message);
    } else {
      toast.success(`使用者權限已更新為: ${newAdminStatus ? '管理員' : '普通用戶'}`);
      fetchUsers(); // Refresh the list
    }
  };


  if (loading) {
    return <div>讀取中...</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">會員管理</h1>
        {/* TODO: Add "New Member" button and dialog */}
        <Button disabled>新增會員</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>名稱</TableHead>
              <TableHead>角色</TableHead>
              <TableHead>註冊時間</TableHead>
              <TableHead>
                <span className="sr-only">操作</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length > 0 ? (
              users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.email}</TableCell>
                  <TableCell>{user.name || '-'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs ${user.is_admin ? 'bg-blue-200 text-blue-800' : 'bg-gray-200 text-gray-800'}`}>
                      {user.is_admin ? 'Admin' : 'Member'}
                    </span>
                  </TableCell>
                  <TableCell>{user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <span className="sr-only">開啟選單</span>
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>操作</DropdownMenuLabel>
                        <DropdownMenuItem
                          onClick={() => handleToggleAdmin(user.id, user.is_admin)}
                        >
                          {user.is_admin ? '撤銷管理員' : '設為管理員'}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  沒有使用者。
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}