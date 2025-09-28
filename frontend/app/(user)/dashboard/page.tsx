"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Database } from '../../../lib/database.types';

type Card = Database['public']['Functions']['get_user_cards']['Returns'][0];

export default function UserDashboardPage() {
  const supabase = createClient();
  const { user, loading: authLoading } = useAuth();
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCards() {
      if (!user) return;

      setLoading(true);
      const { data, error } = await supabase.rpc('get_user_cards');

      if (error) {
        console.error('Error fetching user cards:', error);
        alert('讀取卡片失敗');
      } else {
        setCards(data || []);
      }
      setLoading(false);
    }

    if (!authLoading && user) {
      fetchCards();
    } else if (!authLoading && !user) {
      setLoading(false);
    }
  }, [user, authLoading, supabase]);

  if (authLoading || loading) {
    return <div className="p-8">讀取中...</div>;
  }

  if (!user) {
    return <div className="p-8">請先登入。</div>;
  }

  return (
    <div className="p-4 md:p-8">
      <h1 className="text-2xl font-bold mb-6">我的儀表盤</h1>

      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">我的卡片</h2>
        {cards.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cards.map((card) => (
              <Link href={`/qr/${card.card_id}`} key={card.card_id} className="block group">
                <div className="p-6 bg-gray-700 border border-gray-600 rounded-lg shadow-sm hover:bg-gray-600 transition-shadow">
                  <div className="mb-2">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      card.card_type === 'personal' ? 'bg-green-900 text-green-200' : 'bg-indigo-900 text-indigo-200'
                    }`}>
                      {card.card_type === 'personal' ? '個人卡' : '企業卡'}
                    </span>
                  </div>
                  <h5 className="mb-2 text-xl font-bold tracking-tight text-white group-hover:text-blue-400">
                    {card.card_no}
                  </h5>
                  <p className="font-normal text-gray-300">
                    餘額: <span className="font-semibold">${card.balance?.toLocaleString() || '0.00'}</span>
                  </p>
                  <p className="font-normal text-gray-300">
                    狀態: <span className="font-semibold">{card.status}</span>
                  </p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">您目前沒有任何卡片。</p>
        )}
      </div>
    </div>
  );
}