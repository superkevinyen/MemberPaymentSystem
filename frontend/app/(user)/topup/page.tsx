'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client-browser';
import { callRpcWithIdem } from '@/lib/supabase/rpc';

type PersonalCard = {
  id: string;
  card_no: string;
  balance: number;
};

export default function TopupPage() {
  const router = useRouter();
  const supabase = createClient();

  const [personalCard, setPersonalCard] = useState<PersonalCard | null>(null);
  const [amount, setAmount] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isCardLoading, setIsCardLoading] = useState(true);

  useEffect(() => {
    const fetchPersonalCard = async () => {
      setIsCardLoading(true);
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data: cardData, error } = await supabase
          .from('personal_cards')
          .select('id, card_no, balance')
          .eq('member_id', user.id)
          .single();
        
        if (cardData) {
          setPersonalCard(cardData);
        }
      }
      setIsCardLoading(false);
    };

    fetchPersonalCard();
  }, [supabase]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!personalCard || !amount || Number(amount) <= 0) {
      alert('请输入有效的储值金额');
      return;
    }

    setIsLoading(true);
    try {
      await callRpcWithIdem(
        'user_recharge_personal_card',
        {
          p_personal_card_id: personalCard.id,
          p_amount: Number(amount),
          p_payment_method: 'wechat', // 示例支付方式
          p_reason: '用户在线储值',
        },
        { successMessage: `成功储值 ${amount} 元！` }
      );
      
      // 成功后清空输入框并刷新页面数据
      setAmount('');
      router.refresh(); 
      // 手动更新 state 以立即反馈
      setPersonalCard(prev => prev ? {...prev, balance: prev.balance + Number(amount)} : null);

    } catch (error: any) {
      // 错误已由 callRpc 自动 toast，这里仅记录日志
      console.error('Top-up failed:', error.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isCardLoading) {
    return <div className="p-6 text-center">正在加载您的卡片信息...</div>;
  }
  
  if(!personalCard) {
    return <div className="p-6 text-center text-red-500">未找到您的个人卡信息。</div>;
  }
  
  return (
    <div className="p-6 md:p-8 max-w-lg mx-auto">
      <h1 className="text-3xl font-bold tracking-tight mb-6">个人卡储值</h1>
      <div className="bg-white border rounded-lg shadow-md p-8">
        <div className="mb-6">
            <p className="text-sm text-gray-500">储值卡号</p>
            <p className="text-lg font-mono tracking-wider">{personalCard.card_no}</p>
            <p className="mt-4 text-3xl font-bold">¥{personalCard.balance.toFixed(2)}</p>
            <p className="text-sm text-gray-500">当前余额</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="amount" className="block text-sm font-medium text-gray-700">
              储值金额
            </label>
            <div className="mt-1 relative rounded-md shadow-sm">
                 <div className="pointer-events-none absolute inset-y-0 left-0 pl-3 flex items-center">
                    <span className="text-gray-500 sm:text-sm">¥</span>
                </div>
                <input
                    id="amount"
                    type="number"
                    min="1"
                    step="0.01"
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 pl-7"
                    placeholder="请输入金额"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    disabled={isLoading}
                />
            </div>
          </div>

          {/* 可以在此扩展支付方式选择 */}

          <button
            type="submit"
            disabled={isLoading || !personalCard}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
          >
            {isLoading ? '处理中...' : '确认储值'}
          </button>
        </form>
      </div>
    </div>
  );
}
