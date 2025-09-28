"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from 'react-hot-toast';
import { Database } from '@/lib/database.types';
import { CreditCard, RefreshCw, Receipt } from 'lucide-react';

type Transaction = Database['public']['Functions']['get_transactions']['Returns'][0];

export default function MerchantDashboardPage() {
  const supabase = createClient();
  const { user, loading: authLoading } = useAuth();
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    todayTotal: 0,
    todayCount: 0,
    weekTotal: 0,
    weekCount: 0,
  });

  // 獲取最近交易紀錄
  async function fetchRecentTransactions() {
    if (!user) return;

    setLoading(true);
    const { data, error } = await supabase.rpc('get_transactions', {
      p_limit: 10,
      p_offset: 0,
    });

    if (error) {
      toast.error('讀取交易紀錄失敗: ' + error.message);
      setRecentTransactions([]);
    } else {
      setRecentTransactions(data || []);
      calculateStats(data || []);
    }
    setLoading(false);
  }

  // 計算統計數據
  function calculateStats(transactions: Transaction[]) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const todayTxs = transactions.filter(tx => 
      new Date(tx.created_at) >= today && tx.status === 'completed'
    );
    const weekTxs = transactions.filter(tx => 
      new Date(tx.created_at) >= weekAgo && tx.status === 'completed'
    );

    setStats({
      todayTotal: todayTxs.reduce((sum, tx) => sum + tx.final_amount, 0),
      todayCount: todayTxs.length,
      weekTotal: weekTxs.reduce((sum, tx) => sum + tx.final_amount, 0),
      weekCount: weekTxs.length,
    });
  }

  useEffect(() => {
    if (!authLoading && user) {
      fetchRecentTransactions();
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

  return (
    <div className="p-4 md:p-8">
      <h1 className="text-2xl font-bold mb-6">商家儀表板</h1>
      
      {/* 統計卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日營業額</CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${stats.todayTotal.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {stats.todayCount} 筆交易
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">本週營業額</CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${stats.weekTotal.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {stats.weekCount} 筆交易
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均客單價</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${stats.todayCount > 0 ? (stats.todayTotal / stats.todayCount).toFixed(0) : '0'}
            </div>
            <p className="text-xs text-muted-foreground">
              今日平均
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">交易成功率</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {recentTransactions.length > 0 
                ? ((recentTransactions.filter(tx => tx.status === 'completed').length / recentTransactions.length) * 100).toFixed(1)
                : '0'
              }%
            </div>
            <p className="text-xs text-muted-foreground">
              最近 10 筆交易
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 快速操作 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Link href="/merchant/charge">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <CreditCard className="h-5 w-5 mr-2" />
                收款
              </CardTitle>
              <CardDescription>
                掃描顧客 QR Code 進行收款
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                輸入商家代碼和顧客 QR Code 完成交易
              </p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/merchant/refund">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <RefreshCw className="h-5 w-5 mr-2" />
                退款
              </CardTitle>
              <CardDescription>
                處理交易退款
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                輸入原始交易單號進行退款處理
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* 最近交易 */}
      <Card>
        <CardHeader>
          <CardTitle>最近交易</CardTitle>
          <CardDescription>最新的 10 筆交易紀錄</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>交易單號</TableHead>
                <TableHead>類型</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>金額</TableHead>
                <TableHead>時間</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentTransactions.length > 0 ? (
                recentTransactions.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell className="font-mono">{tx.tx_no}</TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        tx.tx_type === 'payment' ? 'bg-green-100 text-green-800' :
                        tx.tx_type === 'refund' ? 'bg-red-100 text-red-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {tx.tx_type === 'payment' ? '收款' : 
                         tx.tx_type === 'refund' ? '退款' : '儲值'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        tx.status === 'completed' ? 'bg-green-100 text-green-800' :
                        tx.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {tx.status === 'completed' ? '完成' :
                         tx.status === 'processing' ? '處理中' :
                         tx.status === 'failed' ? '失敗' : tx.status}
                      </span>
                    </TableCell>
                    <TableCell>${tx.final_amount.toLocaleString()}</TableCell>
                    <TableCell>{new Date(tx.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center text-gray-500">
                    沒有交易紀錄
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
