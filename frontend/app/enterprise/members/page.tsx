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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from 'react-hot-toast';
import { Database } from '@/lib/database.types';

type UserCard = Database['public']['Functions']['get_user_cards']['Returns'][0];
type BoundMember = Database['public']['Functions']['enterprise_get_bound_members']['Returns'][0];

export default function EnterpriseMembersPage() {
  const supabase = createClient();
  const { user, loading: authLoading } = useAuth();
  
  const [enterpriseCards, setEnterpriseCards] = useState<UserCard[]>([]);
  const [selectedCard, setSelectedCard] = useState<UserCard | null>(null);
  const [boundMembers, setBoundMembers] = useState<BoundMember[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 新增成員對話框狀態
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newMemberNo, setNewMemberNo] = useState('');
  const [cardPassword, setCardPassword] = useState('');

  // 獲取用戶的企業卡
  async function fetchEnterpriseCards() {
    if (!user) return;

    const { data, error } = await supabase.rpc('get_user_cards');
    
    if (error) {
      toast.error('讀取企業卡失敗: ' + error.message);
      return;
    }

    const enterpriseCardsOnly = data?.filter(card => card.card_type === 'enterprise') || [];
    setEnterpriseCards(enterpriseCardsOnly);
    
    // 如果只有一張企業卡，自動選擇
    if (enterpriseCardsOnly.length === 1) {
      setSelectedCard(enterpriseCardsOnly[0]);
    }
  }

  // 獲取選定企業卡的綁定成員
  async function fetchBoundMembers() {
    if (!selectedCard) return;

    setLoading(true);
    const { data, error } = await supabase.rpc('enterprise_get_bound_members', {
      p_card_no: selectedCard.card_no,
    });

    if (error) {
      toast.error('讀取綁定成員失敗: ' + error.message);
      setBoundMembers([]);
    } else {
      setBoundMembers(data || []);
    }
    setLoading(false);
  }

  // 新增成員
  async function handleAddMember() {
    if (!selectedCard || !newMemberNo || !cardPassword) {
      toast.error('請填寫所有必填欄位');
      return;
    }

    const toastId = toast.loading('正在新增成員...');
    const { error } = await supabase.rpc('enterprise_add_member', {
      p_card_no: selectedCard.card_no,
      p_member_no: newMemberNo,
      p_card_password: cardPassword,
    });

    if (error) {
      toast.error('新增成員失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('成員已成功新增！', { id: toastId });
      setNewMemberNo('');
      setCardPassword('');
      setIsAddDialogOpen(false);
      fetchBoundMembers();
    }
  }

  // 移除成員
  async function handleRemoveMember(memberNo: string) {
    if (!selectedCard) return;

    const toastId = toast.loading('正在移除成員...');
    const { error } = await supabase.rpc('enterprise_remove_member', {
      p_card_no: selectedCard.card_no,
      p_member_no: memberNo,
    });

    if (error) {
      toast.error('移除成員失敗: ' + error.message, { id: toastId });
    } else {
      toast.success('成員已移除！', { id: toastId });
      fetchBoundMembers();
    }
  }

  useEffect(() => {
    if (!authLoading && user) {
      fetchEnterpriseCards();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, user]);

  useEffect(() => {
    if (selectedCard) {
      fetchBoundMembers();
    }
  }, [selectedCard]);

  if (authLoading) {
    return <div className="p-8 text-center">讀取中...</div>;
  }

  if (!user) {
    return <div className="p-8 text-center text-red-600">請先登入</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">企業成員管理</h1>
        {selectedCard && (
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button>新增成員</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>新增企業成員</DialogTitle>
                <DialogDescription>
                  將現有會員綁定到企業卡 {selectedCard.card_no}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="member-no" className="text-right">會員號</Label>
                  <Input 
                    id="member-no" 
                    value={newMemberNo} 
                    onChange={(e) => setNewMemberNo(e.target.value)} 
                    className="col-span-3"
                    placeholder="例如: M00000001"
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="card-password" className="text-right">卡片密碼</Label>
                  <Input 
                    id="card-password" 
                    type="password"
                    value={cardPassword} 
                    onChange={(e) => setCardPassword(e.target.value)} 
                    className="col-span-3"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" onClick={handleAddMember}>新增成員</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* 企業卡選擇 */}
      {enterpriseCards.length > 1 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>選擇企業卡</CardTitle>
            <CardDescription>選擇要管理成員的企業卡</CardDescription>
          </CardHeader>
          <CardContent>
            <Select 
              value={selectedCard?.card_id || ''} 
              onValueChange={(value) => {
                const card = enterpriseCards.find(c => c.card_id === value);
                setSelectedCard(card || null);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="請選擇企業卡" />
              </SelectTrigger>
              <SelectContent>
                {enterpriseCards.map((card) => (
                  <SelectItem key={card.card_id} value={card.card_id}>
                    {card.card_no} - ${card.balance?.toLocaleString()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
      )}

      {/* 成員列表 */}
      {selectedCard ? (
        <Card>
          <CardHeader>
            <CardTitle>綁定成員列表</CardTitle>
            <CardDescription>
              企業卡 {selectedCard.card_no} 的綁定成員
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">讀取中...</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>會員號</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>電話</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>綁定時間</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {boundMembers.length > 0 ? (
                    boundMembers.map((member) => (
                      <TableRow key={member.member_id}>
                        <TableCell className="font-mono">{member.member_no}</TableCell>
                        <TableCell>{member.name || '-'}</TableCell>
                        <TableCell>{member.phone || '-'}</TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            member.role === 'admin' 
                              ? 'bg-blue-100 text-blue-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {member.role === 'admin' ? '管理員' : '成員'}
                          </span>
                        </TableCell>
                        <TableCell>{new Date(member.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          {member.role !== 'admin' && (
                            <Button 
                              variant="destructive" 
                              size="sm"
                              onClick={() => handleRemoveMember(member.member_no)}
                            >
                              移除
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={6} className="h-24 text-center text-gray-500">
                        沒有綁定的成員
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-gray-500">
              {enterpriseCards.length === 0 
                ? '您沒有任何企業卡' 
                : '請選擇要管理的企業卡'
              }
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
