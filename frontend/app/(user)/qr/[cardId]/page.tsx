'use client';

import { useParams, useSearchParams } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import { callRpc } from '@/lib/supabase/rpc';
import useCountdown from '@/hooks/useCountdown';
import { createClient } from '@/lib/supabase/client-browser';

type QrCodeData = {
  qr_plain: string;
  qr_expires_at: string;
};

export default function QrCodePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const cardId = params.cardId as string;
  // 从 URL query 获取卡类型，这是一个重要的上下文信息
  const cardType = searchParams.get('type') as 'personal' | 'enterprise';

  const [qrData, setQrData] = useState<QrCodeData | null>(null);
  const [cardNo, setCardNo] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const timeLeft = useCountdown(qrData?.qr_expires_at ?? null);
  const isExpired = timeLeft === 0 && !!qrData;

  const fetchQrCode = useCallback(async () => {
    if (!cardId || !cardType) {
      setError('缺少卡片ID或类型信息');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    try {
      const data = await callRpc<QrCodeData>(
        'rotate_card_qr',
        { p_card_id: cardId, p_card_type: cardType },
        { autoToast: false } // 手动处理Toast，因为UI交互更复杂
      );
      setQrData(data);
    } catch (e: any) {
      console.error(e);
      setError(e.message || '无法获取二维码，请重试');
    } finally {
      setIsLoading(false);
    }
  }, [cardId, cardType]);
  
  // 组件加载时获取卡号用于显示
  useEffect(() => {
    const fetchCardDetails = async () => {
        const supabase = createClient();
        const tableName = cardType === 'personal' ? 'personal_cards' : 'enterprise_cards';
        const { data, error } = await supabase.from(tableName).select('card_no').eq('id', cardId).single();
        if(data) setCardNo(data.card_no);
    };
    fetchCardDetails();
    fetchQrCode();
  }, [fetchQrCode, cardId, cardType]);

  return (
    <div className="p-6 md:p-8 max-w-md mx-auto text-center flex flex-col items-center">
        <div className="w-full bg-white border rounded-lg shadow-lg p-8">
            <h1 className="text-xl font-semibold mb-2">付款码</h1>
            <p className="text-gray-500 font-mono tracking-wider mb-6">{cardNo || '加载中...'}</p>
            
            <div className="relative w-64 h-64 mx-auto">
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-100 rounded-lg">
                        <p>正在生成...</p>
                    </div>
                )}
                {error && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-red-50 border-red-200 border rounded-lg p-4">
                        <p className="font-semibold text-red-700">加载失败</p>
                        <p className="text-sm text-red-600 mt-2">{error}</p>
                    </div>
                )}
                {qrData && !isLoading && !error && (
                    <>
                        <QRCodeCanvas
                            value={qrData.qr_plain}
                            size={256}
                            className={`transition-opacity duration-300 ${isExpired ? 'opacity-10' : 'opacity-100'}`}
                        />
                         {isExpired && (
                            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-80">
                                <span className="text-lg font-bold text-red-500">已过期</span>
                            </div>
                        )}
                    </>
                )}
            </div>
            
            <div className="mt-6">
                <p className="text-lg">
                    {isExpired ? '请刷新二维码' : `剩余有效时间: ${timeLeft} 秒`}
                </p>
                <p className="text-sm text-gray-400 mt-1">
                    每15分钟自动刷新
                </p>
            </div>
            
             <button
                onClick={fetchQrCode}
                disabled={isLoading}
                className="mt-6 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
            >
                {isLoading ? '刷新中...' : '刷新'}
            </button>
        </div>
    </div>
  );
}
