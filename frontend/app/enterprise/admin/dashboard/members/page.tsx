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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MoreHorizontal } from "lucide-react";
import { toast } from 'react-hot-toast';

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

  // State for the 'Create' dialog
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('');

  // State for the 'Edit' dialog
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [editName, setEditName] = useState('');
  const [editPhone, setEditPhone] = useState('');

  async function fetchMembers() {
    if (!currentUser || !isAdmin) {
      setLoading(false);
      return;
    }

    setLoading(true);
    const { data: membersData, error } = await supabase.rpc('get_all_member_profiles');
    
    if (error) {
      toast.error('讀取會員列表失敗: ' + error.message);
      setMembers([]);
    } else {
      setMembers(membersData || []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (!authLoading && currentUser && isAdmin) {
      fetchMembers();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, currentUser, isAdmin]);

  const handleCreateMember = async () => {
    if (!newEmail || !newPassword || !newName) {
      toast.error('信箱、密碼和姓名為必填項。');
      return;
    }

    const toastId = toast.loading('正在建立會員...');
    const { data, error } = await supabase.rpc('admin_create_user', {
      p_email: newEmail,
      p_password: newPassword,
      p_name: newName,
      p_phone: newPhone,
    });

    if (error) {
      toast.error('建立會員失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('會員已成功建立！', { id: toastId });
      setNewEmail('');
      setNewPassword('');
      setNewName('');
      setNewPhone('');
      setIsCreateDialogOpen(false);
      fetchMembers(); // Refresh the list
    }
  };

  const openEditDialog = (member: Member) => {
    setSelectedMember(member);
    setEditName(member.name || '');
    setEditPhone(member.phone || '');
    setIsEditDialogOpen(true);
  };
  
  const handleUpdateMember = async () => {
    if (!selectedMember) return;
  
    const toastId = toast.loading('正在更新會員資料...');
    const { error } = await supabase.rpc('admin_update_member_profile', {
      p_member_id: selectedMember.id,
      p_name: editName,
      p_phone: editPhone,
    });
  
    if (error) {
      toast.error('更新失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('會員資料已更新！', { id: toastId });
      setIsEditDialogOpen(false);
      fetchMembers();
    }
  };

  const handleToggleMemberStatus = async (member_id: string, current_status: string) => {
    const newStatus = current_status === 'active' ? 'inactive' : 'active';
    
    const toastId = toast.loading('正在更新會員狀態...');
    const { error } = await supabase.rpc('admin_update_member_status', {
      p_member_id: member_id,
      p_status: newStatus,
    });

    if (error) {
      toast.error('更新會員狀態失敗: ' + error.message, { id: toastId });
    } else {
      toast.success(`會員狀態已更新`, { id: toastId });
      fetchMembers();
    }
  };

  if (authLoading || loading) {
    return <div className="p-10 text-center">讀取中...</div>;
  }

  if (!currentUser || !isAdmin) {
    return <div className="p-10 text-center text-red-600">權限不足：只有平台管理員可以訪問此頁面</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">會員管理</h1>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>新增會員</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>新增會員</DialogTitle>
              <DialogDescription>建立一個新的會員帳戶。</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="email" className="text-right">信箱</Label>
                <Input id="email" type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} className="col-span-3"/>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="password" className="text-right">密碼</Label>
                <Input id="password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="col-span-3"/>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="name" className="text-right">姓名</Label>
                <Input id="name" value={newName} onChange={(e) => setNewName(e.target.value)} className="col-span-3"/>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="phone" className="text-right">電話</Label>
                <Input id="phone" value={newPhone} onChange={(e) => setNewPhone(e.target.value)} className="col-span-3"/>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" onClick={handleCreateMember}>建立</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
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
              <TableHead><span className="sr-only">操作</span></TableHead>
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
                        <DropdownMenuItem onClick={() => openEditDialog(member)}>編輯</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleToggleMemberStatus(member.id, member.status)}>
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
                  目前沒有會員資料
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>編輯會員資料</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="edit-name" className="text-right">姓名</Label>
              <Input id="edit-name" value={editName} onChange={(e) => setEditName(e.target.value)} className="col-span-3"/>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="edit-phone" className="text-right">電話</Label>
              <Input id="edit-phone" value={editPhone} onChange={(e) => setEditPhone(e.target.value)} className="col-span-3"/>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" onClick={handleUpdateMember}>儲存變更</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}