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

type Enterprise = {
  id: string; // This is the enterprise_card id
  company_name: string | null;
  card_id: string;
  card_no: string | null;
  balance: number | null;
  fixed_discount: number | null;
  card_status: string | null;
  created_at: string | null;
};

export default function EnterprisesPage() {
  const supabase = createClient();
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [loading, setLoading] = useState(true);
  
  // State for the 'Create' dialog
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newPassword, setNewPassword] = useState('');

  // State for the 'Edit' dialog
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [selectedEnterprise, setSelectedEnterprise] = useState<Enterprise | null>(null);
  const [editCompanyName, setEditCompanyName] = useState('');
  const [editFixedDiscount, setEditFixedDiscount] = useState(1.0);

  async function fetchEnterprises() {
    setLoading(true);
    const { data, error } = await supabase.rpc('get_all_enterprises_for_admin');
    if (error) {
      toast.error('讀取企業列表失敗: ' + error.message);
      console.error(error);
    } else {
      setEnterprises(data || []);
    }
    setLoading(false);
  }

  useEffect(() => {
    fetchEnterprises();
  }, []);

  const handleCreateEnterprise = async () => {
    if (!newCompanyName || !newPassword) {
      toast.error('公司名稱和密碼為必填項。');
      return;
    }

    const toastId = toast.loading('正在建立企業...');
    const { data, error } = await supabase.rpc('admin_create_enterprise_and_card', {
      p_company_name: newCompanyName,
      p_password: newPassword,
    });

    if (error) {
      toast.error('建立企業失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('企業已成功建立！', { id: toastId });
      setNewCompanyName('');
      setNewPassword('');
      setIsCreateDialogOpen(false);
      fetchEnterprises(); // Refresh the list
    }
  };

  const openEditDialog = (enterprise: Enterprise) => {
    setSelectedEnterprise(enterprise);
    setEditCompanyName(enterprise.company_name || '');
    setEditFixedDiscount(enterprise.fixed_discount || 1.0);
    setIsEditDialogOpen(true);
  };

  const handleUpdateEnterprise = async () => {
    if (!selectedEnterprise) return;

    const toastId = toast.loading('正在更新企業資訊...');
    const { error } = await supabase.rpc('admin_update_enterprise_card_details', {
      p_card_id: selectedEnterprise.card_id,
      p_company_name: editCompanyName,
      p_fixed_discount: editFixedDiscount,
    });

    if (error) {
      toast.error('更新失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('企業資訊已更新！', { id: toastId });
      setIsEditDialogOpen(false);
      fetchEnterprises();
    }
  };

  const handleUpdateStatus = async (card_id: string, new_status: 'active' | 'inactive') => {
    const toastId = toast.loading('正在更新狀態...');
    const { error } = await supabase.rpc('admin_update_enterprise_card_status', {
      p_card_id: card_id,
      p_status: new_status,
    });

    if (error) {
      toast.error('狀態更新失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('狀態已更新！', { id: toastId });
      fetchEnterprises();
    }
  };

  if (loading) {
    return <div className="p-10">讀取中...</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">企業管理</h1>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>新增企業</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>新增企業</DialogTitle>
              <DialogDescription>建立一個新的企業帳戶及其對應的企業卡。</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="companyName" className="text-right">公司名稱</Label>
                <Input id="companyName" value={newCompanyName} onChange={(e) => setNewCompanyName(e.target.value)} className="col-span-3"/>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="password" className="text-right">卡片密碼</Label>
                <Input id="password" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="col-span-3"/>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" onClick={handleCreateEnterprise}>建立</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>公司名稱</TableHead>
              <TableHead>企業卡號</TableHead>
              <TableHead>餘額</TableHead>
              <TableHead>折扣</TableHead>
              <TableHead>狀態</TableHead>
              <TableHead>建立時間</TableHead>
              <TableHead><span className="sr-only">操作</span></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {enterprises.length > 0 ? (
              enterprises.map((enterprise) => (
                <TableRow key={enterprise.id}>
                  <TableCell className="font-medium">{enterprise.company_name}</TableCell>
                  <TableCell>{enterprise.card_no}</TableCell>
                  <TableCell>${enterprise.balance?.toLocaleString()}</TableCell>
                  <TableCell>{enterprise.fixed_discount}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      enterprise.card_status === 'active'
                        ? 'bg-green-100 text-green-800 border border-green-200'
                        : 'bg-red-100 text-red-800 border border-red-200'
                    }`}>
                      {enterprise.card_status === 'active' ? '啟用' : '停用'}
                    </span>
                  </TableCell>
                  <TableCell>{enterprise.created_at ? new Date(enterprise.created_at).toLocaleDateString() : '-'}</TableCell>
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
                        <DropdownMenuItem onClick={() => openEditDialog(enterprise)} className="cursor-pointer">編輯</DropdownMenuItem>
                        {enterprise.card_status === 'active' ? (
                          <DropdownMenuItem onClick={() => handleUpdateStatus(enterprise.card_id, 'inactive')} className="cursor-pointer">停用</DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => handleUpdateStatus(enterprise.card_id, 'active')} className="cursor-pointer">啟用</DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">沒有企業資料。</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>編輯企業資訊</DialogTitle>
            <DialogDescription>修改企業的詳細資料。</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="editCompanyName" className="text-right">公司名稱</Label>
              <Input id="editCompanyName" value={editCompanyName} onChange={(e) => setEditCompanyName(e.target.value)} className="col-span-3"/>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="editFixedDiscount" className="text-right">固定折扣</Label>
              <Input id="editFixedDiscount" type="number" step="0.01" value={editFixedDiscount} onChange={(e) => setEditFixedDiscount(parseFloat(e.target.value))} className="col-span-3"/>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" onClick={handleUpdateEnterprise}>儲存變更</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}