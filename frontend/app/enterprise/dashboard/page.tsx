"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Database } from '@/lib/database.types';

type UserCard = Database['public']['Functions']['get_user_cards']['Returns'][0];

export default function EnterpriseDashboardPage() {
  const supabase = createClient();
  const { user, loading: authLoading } = useAuth();
  const [enterpriseCards, setEnterpriseCards] = useState<UserCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEnterpriseCards() {
      if (!user) return;

      setLoading(true);
      const { data, error } = await supabase.rpc('get_user_cards');

      if (error) {
        console.error('Error fetching user cards:', error);
      } else {
        // 只顯示企業卡
        const enterpriseCardsOnly = data?.filter(card => card.card_type === 'enterprise') || [];
        setEnterpriseCards(enterpriseCardsOnly);
      }
      setLoading(false);
    }

    if (!authLoading && user) {
      fetchEnterpriseCards();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [user, authLoading, supabase]);

  if (authLoading || loading) {
    return <div className="p-8 text-center">讀取中...</div>;
  }

  if (!user) {
    return <div className="p-8 text-center text-red-600">請先登入</div>;
  }

  if (enterpriseCards.length === 0) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">企業儀表板</h1>
        <p className="text-gray-600">您目前沒有任何企業卡。</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8">
      <h1 className="text-2xl font-bold mb-6">企業儀表板</h1>

      {/* 企業卡片列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {enterpriseCards.map((card) => (
          <Card key={card.card_id} className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
            <CardHeader>
              <CardTitle className="flex justify-between items-center">
                <span>企業卡</span>
                <span className={`px-2 py-1 rounded-full text-xs ${
                  card.status === 'active' 
                    ? 'bg-green-500 text-white' 
                    : 'bg-red-500 text-white'
                }`}>
                  {card.status === 'active' ? '啟用' : '停用'}
                </span>
              </CardTitle>
              <CardDescription className="text-blue-100">
                卡號: {card.card_no}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>餘額:</span>
                  <span className="font-bold text-xl">${card.balance?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>折扣:</span>
                  <span>{((1 - card.discount) * 100).toFixed(1)}% OFF</span>
                </div>
                <div className="flex justify-between">
                  <span>建立時間:</span>
                  <span>{new Date(card.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              
              <div className="mt-4 space-y-2">
                <Link href={`/qr/${card.card_id}`} className="block">
                  <Button variant="secondary" className="w-full">
                    顯示 QR Code
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 管理功能區域 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* 成員管理 */}
        <Link href="/enterprise/members" className="block">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="text-lg">成員管理</CardTitle>
              <CardDescription>
                管理企業卡綁定的成員
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                新增、移除或查看企業卡的綁定成員
              </p>
            </CardContent>
          </Card>
        </Link>

        {/* 儲值功能 */}
        <Link href="/enterprise/topup" className="block">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="text-lg">企業卡儲值</CardTitle>
              <CardDescription>
                為企業卡增加餘額
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                透過各種付款方式為企業卡充值
              </p>
            </CardContent>
          </Card>
        </Link>

        {/* 交易紀錄 */}
        <Link href="/enterprise/admin/dashboard/transactions" className="block">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="text-lg">交易紀錄</CardTitle>
              <CardDescription>
                查看企業卡交易歷史
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                檢視所有相關的付款和退款紀錄
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
