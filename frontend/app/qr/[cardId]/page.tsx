"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { useCountdown } from '@/hooks/useCountdown';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from 'react-hot-toast';
import { QRCodeSVG } from 'qrcode.react';
import { RefreshCw } from 'lucide-react';

type UserCard = {
  card_id: string;
  card_type: 'personal' | 'enterprise';
  card_no: string;
  balance: number;
  level: number | null;
  discount: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export default function QRCodePage() {
  const params = useParams();
  const cardId = params.cardId as string;
  const supabase = createClient();
  const { user, loading: authLoading } = useAuth();
  
  const [card, setCard] = useState<UserCard | null>(null);
  const [qrData, setQrData] = useState<{ qr_plain: string; qr_expires_at: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // 計算 QR Code 剩餘時間
  const { minutes, seconds, isExpired } = useCountdown(qrData?.qr_expires_at || null);

  // 獲取用戶卡片資訊
  async function fetchCard() {
    if (!user) return;

    const { data: cardsData, error } = await supabase.rpc('get_user_cards');
    
    if (error) {
      toast.error('讀取卡片資訊失敗: ' + error.message);
      return;
    }

    const foundCard = cardsData?.find(c => c.card_id === cardId);
    if (!foundCard) {
      toast.error('找不到指定的卡片或您沒有權限訪問');
      return;
    }

    setCard(foundCard);
  }

  // 生成或刷新 QR Code
  async function generateQRCode() {
    if (!card) return;

    setRefreshing(true);
    const { data, error } = await supabase.rpc('rotate_card_qr', {
      p_card_id: cardId,
      p_card_type: card.card_type,
    });

    if (error) {
      toast.error('生成 QR Code 失敗: ' + error.message);
    } else if (data && data.length > 0) {
      setQrData(data[0]);
      toast.success('QR Code 已更新');
    }
    setRefreshing(false);
  }

  useEffect(() => {
    if (!authLoading && user) {
      fetchCard();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, user, cardId]);

  useEffect(() => {
    if (card) {
      generateQRCode();
      setLoading(false);
    }
  }, [card]);

  // 自動刷新過期的 QR Code
  useEffect(() => {
    if (isExpired && card) {
      generateQRCode();
    }
  }, [isExpired, card]);

  if (authLoading || loading) {
    return <div className="p-8 text-center">讀取中...</div>;
  }

  if (!user) {
    return <div className="p-8 text-center text-red-600">請先登入</div>;
  }

  if (!card) {
    return <div className="p-8 text-center text-red-600">找不到指定的卡片</div>;
  }

  return (
    <div className="container mx-auto py-10 flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">
            {card.card_type === 'personal' ? '個人卡' : '企業卡'} QR Code
          </CardTitle>
          <CardDescription className="text-center">
            向商家出示此 QR Code 進行付款
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 卡片資訊 */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">卡號:</span>
              <span className="font-mono">{card.card_no}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">餘額:</span>
              <span className="font-semibold">${card.balance?.toLocaleString()}</span>
            </div>
            {card.card_type === 'personal' && (
              <>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">等級:</span>
                  <span>Level {card.level}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">折扣:</span>
                  <span>{((1 - card.discount) * 100).toFixed(1)}% OFF</span>
                </div>
              </>
            )}
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">狀態:</span>
              <span className={`px-2 py-1 rounded-full text-xs ${
                card.status === 'active' 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {card.status === 'active' ? '啟用' : '停用'}
              </span>
            </div>
          </div>

          {/* QR Code 區域 */}
          {card.status === 'active' ? (
            <div className="text-center space-y-4">
              {qrData ? (
                <>
                  <div className="flex justify-center p-4 bg-white rounded-lg">
                    <QRCodeSVG 
                      value={qrData.qr_plain} 
                      size={200}
                      level="M"
                      includeMargin={true}
                    />
                  </div>
                  
                  {/* 倒數計時 */}
                  <div className="text-sm text-gray-600">
                    {isExpired ? (
                      <span className="text-red-600">QR Code 已過期</span>
                    ) : (
                      <span>QR Code 將在 {minutes}:{seconds.toString().padStart(2, '0')} 後過期</span>
                    )}
                  </div>

                  {/* 刷新按鈕 */}
                  <Button 
                    onClick={generateQRCode} 
                    disabled={refreshing}
                    variant="outline"
                    className="w-full"
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                    {refreshing ? '生成中...' : '刷新 QR Code'}
                  </Button>
                </>
              ) : (
                <div className="text-center">
                  <Button onClick={generateQRCode} disabled={refreshing}>
                    {refreshing ? '生成中...' : '生成 QR Code'}
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-red-600">
              卡片已停用，無法生成 QR Code
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}