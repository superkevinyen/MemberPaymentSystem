"use client";

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from 'react-hot-toast';
import { Database } from '@/lib/database.types';

type UserCard = Database['public']['Functions']['get_user_cards']['Returns'][0];
type PayMethod = Database['public']['Enums']['pay_method'];

export default function EnterpriseTopupPage() {
  const supabase = createClient();
  const { user, loading: authLoading } = useAuth();
  
  const [enterpriseCards, setEnterpriseCards] = useState<UserCard[]>([]);
  const [selectedCard, setSelectedCard] = useState<UserCard | null>(null);
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<PayMethod>('wechat');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  // 獲取用戶的企業卡
  async function fetchEnterpriseCards() {
    if (!user) return;

    setLoading(true);
    const { data, error } = await supabase.rpc('get_user_cards');
    
    if (error) {
      toast.error('讀取企業卡失敗: ' + error.message);
    } else {
      const enterpriseCardsOnly = data?.filter(card => card.card_type === 'enterprise') || [];
      setEnterpriseCards(enterpriseCardsOnly);
      
      // 如果只有一張企業卡，自動選擇
      if (enterpriseCardsOnly.length === 1) {
        setSelectedCard(enterpriseCardsOnly[0]);
      }
    }
    setLoading(false);
  }

  // 處理儲值
  async function handleTopup() {
    if (!selectedCard || !amount) {
      toast.error('請選擇企業卡並輸入儲值金額');
      return;
    }

    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      toast.error('請輸入有效的儲值金額');
      return;
    }

    setProcessing(true);
    const toastId = toast.loading('正在處理儲值...');

    const { data, error } = await supabase.rpc('user_recharge_enterprise_card_admin', {
      p_enterprise_card_id: selectedCard.card_id,
      p_amount: amountNum,
      p_payment_method: paymentMethod,
      p_reason: reason || '企業卡儲值',
    });

    if (error) {
      toast.error('儲值失敗: ' + error.message, { id: toastId });
    } else {
      toast.success(
        (t) => (
          <div className="flex flex-col">
            <b>儲值成功！</b>
            <span>交易單號: {data[0]?.tx_no}</span>
            <span>儲值金額: ${data[0]?.amount.toLocaleString()}</span>
          </div>
        ),
        { id: toastId, duration: 6000 }
      );
      
      // 重置表單
      setAmount('');
      setReason('');
      
      // 重新獲取卡片資訊以更新餘額
      fetchEnterpriseCards();
    }
    setProcessing(false);
  }

  useEffect(() => {
    if (!authLoading && user) {
      fetchEnterpriseCards();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, user]);

  if (authLoading || loading) {
    return <div className="p-8 text-center">讀取中...</div>;
  }

  if (!user) {
    return <div className="p-8 text-center text-red-600">請先登入</div>;
  }

  if (enterpriseCards.length === 0) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold mb-4">企業卡儲值</h1>
        <p className="text-gray-600">您目前沒有任何企業卡。</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-10 flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>企業卡儲值</CardTitle>
          <CardDescription>為您的企業卡增加餘額</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 企業卡選擇 */}
          {enterpriseCards.length > 1 ? (
            <div className="space-y-2">
              <Label>選擇企業卡</Label>
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
            </div>
          ) : (
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">企業卡:</div>
              <div className="font-medium">{enterpriseCards[0]?.card_no}</div>
              <div className="text-sm text-gray-600">
                目前餘額: <span className="font-semibold">${enterpriseCards[0]?.balance?.toLocaleString()}</span>
              </div>
            </div>
          )}

          {selectedCard && (
            <>
              {/* 儲值金額 */}
              <div className="space-y-2">
                <Label htmlFor="amount">儲值金額</Label>
                <Input
                  id="amount"
                  type="number"
                  placeholder="例如: 1000.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  min="0"
                  step="0.01"
                />
              </div>

              {/* 付款方式 */}
              <div className="space-y-2">
                <Label>付款方式</Label>
                <Select value={paymentMethod} onValueChange={(value: PayMethod) => setPaymentMethod(value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="wechat">微信支付</SelectItem>
                    <SelectItem value="alipay">支付寶</SelectItem>
                    <SelectItem value="cash">現金</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* 備註 */}
              <div className="space-y-2">
                <Label htmlFor="reason">備註 (選填)</Label>
                <Input
                  id="reason"
                  placeholder="儲值原因或備註"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>

              {/* 儲值按鈕 */}
              <Button 
                onClick={handleTopup} 
                disabled={processing || !amount} 
                className="w-full"
              >
                {processing ? '處理中...' : `確認儲值 $${amount || '0'}`}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
