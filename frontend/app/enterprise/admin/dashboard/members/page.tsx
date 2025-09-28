"use client";

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
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

// Define the type for our member data to match the RPC function return type
type Member = {
  id: string;
  member_no: string;
  name: string;
  phone: string;
  email: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export default function MembersPage() {
  const supabase = createClient();
  const { user: currentUser, isAdmin, loading: authLoading } = useAuth();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchMembers() {
    if (!currentUser || !isAdmin) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      // 使用正確的 RPC 函數來獲取所有會員資料
      const { data: membersData, error } = await supabase.rpc('get_all_member_profiles');
      
      if (error) {
        console.error('RPC error:', error);
        toast.error('讀取會員列表失敗: ' + error.message);
        setMembers([]);
      } else if (membersData) {
        setMembers(membersData);
      } else {
        setMembers([]);
      }
    } catch (err) {
      console.error('Fetch members error:', err);
      toast.error('發生未知錯誤');
      setMembers([]);
    }
    setLoading(false);
  }

  useEffect(() => {
    // 只有在認證完成且使用者是管理員時才載入資料
    if (!authLoading && currentUser && isAdmin) {
      fetchMembers();
    } else if (!authLoading && (!currentUser || !isAdmin)) {
      setLoading(false);
    }
  }, [authLoading, currentUser, isAdmin]);

  const handleToggleMemberStatus = async (member_id: string, current_status: string) => {
    const newStatus = current_status === 'active' ? 'inactive' : 'active';
    
    try {
      const { error } = await supabase.rpc('admin_update_member_status', {
        p_member_id: member_id,
        p_status: newStatus
      });

      if (error) {
        console.error('Toggle member status error:', error);
        toast.error('更新會員狀態失敗: ' + error.message);
      } else {
        toast.success(`會員狀態已更新為: ${newStatus === 'active' ? '啟用' : '停用'}`);
        // 立即更新本地狀態，避免重新載入整個列表
        setMembers(prevMembers =>
          prevMembers.map(member =>
            member.id === member_id
              ? { ...member, status: newStatus }
              : member
          )
        );
      }
    } catch (err) {
      console.error('Toggle member status error:', err);
      toast.error('更新會員狀態時發生未知錯誤');
    }
  };


  if (authLoading || loading) {
    return (
      <div className="container mx-auto py-10">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">讀取中...</div>
        </div>
      </div>
    );
  }

  // 如果使用者未登入或不是管理員，顯示權限不足訊息
  if (!currentUser || !isAdmin) {
    return (
      <div className="container mx-auto py-10">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg text-red-600">權限不足：只有平台管理員可以訪問此頁面</div>
        </div>
      </div>
    );
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
              <TableHead>會員號</TableHead>
              <TableHead>名稱</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>電話</TableHead>
              <TableHead>狀態</TableHead>
              <TableHead>註冊時間</TableHead>
              <TableHead>
                <span className="sr-only">操作</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.length > 0 ? (
              members.map((member) => (
                <TableRow key={member.id}>
                  <TableCell className="font-medium">{member.member_no}</TableCell>
                  <TableCell>{member.name || '-'}</TableCell>
                  <TableCell>{member.email || '-'}</TableCell>
                  <TableCell>{member.phone || '-'}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      member.status === 'active'
                        ? 'bg-green-100 text-green-800 border border-green-200'
                        : 'bg-red-100 text-red-800 border border-red-200'
                    }`}>
                      {member.status === 'active' ? '啟用' : '停用'}
                    </span>
                  </TableCell>
                  <TableCell>{member.created_at ? new Date(member.created_at).toLocaleDateString() : '-'}</TableCell>
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
                          onClick={() => handleToggleMemberStatus(member.id, member.status)}
                          className="cursor-pointer"
                        >
                          {member.status === 'active' ? '停用會員' : '啟用會員'}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center text-gray-500">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <div>目前沒有會員資料</div>
                    <div className="text-sm">請檢查資料庫連線或聯絡系統管理員</div>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}