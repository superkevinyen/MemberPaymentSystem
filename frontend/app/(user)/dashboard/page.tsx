import { createClient } from '@/lib/supabase/client-server';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import Link from 'next/link';

// 定义从视图中获取的数据类型，以便在组件中使用
// 建议：未来可以将这些类型移动到 lib/supabase/types.ts 中
type UserCard = {
  card_id: string;
  card_type: 'personal' | 'enterprise';
  card_no: string;
  balance: number;
  level: number | null;
  discount: number;
  status: string;
};

type UsageLog = {
  id: string;
  created_at: string;
  tx_type: 'payment' | 'refund' | 'recharge';
  final_amount: number;
  merchant_id: string | null;
  reason: string | null;
};

export default async function DashboardPage() {
  const cookieStore = cookies();
  const supabase = createClient(cookieStore);

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    redirect('/sign-in'); // 假设登录页路由为 /sign-in
  }

  // 并行获取卡片信息和交易记录
  const [cardsResult, logsResult] = await Promise.all([
    supabase.from('v_user_cards').select('*'),
    supabase.from('v_usage_logs').select('*').order('created_at', { ascending: false }).limit(10)
  ]);
  
  const cards: UserCard[] = cardsResult.data || [];
  const logs: UsageLog[] = logsResult.data || [];

  return (
    <div className="p-6 md:p-8 space-y-8">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">会员仪表盘</h1>
        <p className="text-muted-foreground text-gray-500">欢迎回来, {user.email}!</p>
      </header>
      
      <CardSummarySection cards={cards} />
      
      <TransactionHistorySection logs={logs} />
      
    </div>
  );
}

// 卡片信息汇总组件
function CardSummarySection({ cards }: { cards: UserCard[] }) {
  if (cards.length === 0) {
    return (
      <section>
        <h2 className="text-xl font-semibold mb-4">我的卡片</h2>
        <div className="text-center py-10 px-6 border-2 border-dashed rounded-lg">
          <p className="text-gray-500">您还没有任何会员卡。</p>
          <p className="text-sm text-gray-400 mt-2">新用户注册后会自动发放个人卡。</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <h2 className="text-xl font-semibold mb-4">我的卡片</h2>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <div key={card.card_id} className="border rounded-lg p-6 shadow-sm bg-white">
            <div className="flex justify-between items-start">
              <div>
                <p className={`text-sm font-medium ${card.card_type === 'personal' ? 'text-blue-600' : 'text-green-600'}`}>
                  {card.card_type === 'personal' ? '个人卡' : '企业卡'}
                </p>
                <p className="text-lg font-mono tracking-wider">{card.card_no}</p>
              </div>
              <span className="px-2 py-1 text-xs font-semibold text-white bg-gray-700 rounded-full">{card.status}</span>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold">¥{card.balance.toFixed(2)}</p>
              <p className="text-sm text-gray-500">当前余额</p>
            </div>
            <div className="flex justify-between text-sm mt-4 text-gray-600">
              <span>等级: {card.level ?? 'N/A'}</span>
              <span>折扣: {card.discount}</span>
            </div>
             <Link href={`/user/qr/${card.card_id}`} className="mt-4 block w-full text-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
                出示二维码
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}

// 交易历史组件
function TransactionHistorySection({ logs }: { logs: UsageLog[] }) {
  const formatTxType = (type: UsageLog['tx_type']) => {
    switch (type) {
      case 'payment': return <span className="text-red-500">支付</span>;
      case 'refund': return <span className="text-gray-500">退款</span>;
      case 'recharge': return <span className="text-green-500">储值</span>;
      default: return type;
    }
  };

  return (
      <section>
          <h2 className="text-xl font-semibold mb-4">最近交易</h2>
          <div className="border rounded-lg overflow-hidden bg-white">
              <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                      <tr>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日期</th>
                          <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
                          <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">金额 (¥)</th>
                      </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                      {logs.length > 0 ? logs.map(log => (
                          <tr key={log.id}>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{formatTxType(log.tx_type)}</td>
                              <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-semibold ${log.tx_type === 'payment' ? 'text-red-500' : 'text-green-500'}`}>
                                  {log.tx_type === 'payment' ? '-' : '+'}{log.final_amount.toFixed(2)}
                              </td>
                          </tr>
                      )) : (
                          <tr>
                              <td colSpan={3} className="text-center py-10 px-6 text-gray-500">暂无交易记录</td>
                          </tr>
                      )}
                  </tbody>
              </table>
          </div>
      </section>
  );
}
