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
import { toast } from 'react-hot-toast';

// Define the type for our enterprise data based on the RPC return type
type Enterprise = {
  id: string;
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
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  
  // Form state
  const [companyName, setCompanyName] = useState('');
  const [password, setPassword] = useState('');

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
    if (!companyName || !password) {
      toast.error('公司名稱和密碼為必填項。');
      return;
    }

    const toastId = toast.loading('正在建立企業...');
    const { error } = await supabase.rpc('create_company_with_password', {
      company_name: companyName,
      plain_password: password,
    });

    if (error) {
      toast.error('建立企業失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('企業已成功建立！', { id: toastId });
      setCompanyName('');
      setPassword('');
      setIsDialogOpen(false);
      fetchEnterprises(); // Refresh the list
    }
  };

  if (loading) {
    return <div>讀取中...</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">企業管理</h1>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>新增企業</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>新增企業</DialogTitle>
              <DialogDescription>
                建立一個新的企業帳戶及其對應的企業卡。
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="companyName" className="text-right">
                  公司名稱
                </Label>
                <Input
                  id="companyName"
                  value={companyName}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCompanyName(e.target.value)}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="password" className="text-right">
                  卡片密碼
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                  className="col-span-3"
                />
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
              <TableHead>狀態</TableHead>
              <TableHead>建立時間</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {enterprises.length > 0 ? (
              enterprises.map((enterprise) => (
                <TableRow key={enterprise.id}>
                  <TableCell className="font-medium">{enterprise.company_name}</TableCell>
                  <TableCell>{enterprise.card_no}</TableCell>
                  <TableCell>${enterprise.balance?.toLocaleString()}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded-full text-xs ${enterprise.card_status === 'active' ? 'bg-green-200 text-green-800' : 'bg-gray-200 text-gray-800'}`}>
                      {enterprise.card_status}
                    </span>
                  </TableCell>
                  <TableCell>{enterprise.created_at ? new Date(enterprise.created_at).toLocaleDateString() : '-'}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  沒有企業。
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}