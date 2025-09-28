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
import { toast } from 'react-hot-toast';
// We will need a date picker, let's assume we have one from shadcn/ui
// import { DatePicker } from "@/components/ui/date-picker";

type Transaction = {
  id: string;
  tx_no: string;
  card_type: string;
  card_id: string;
  merchant_id: string;
  tx_type: string;
  final_amount: number;
  status: string;
  created_at: string;
  total_count: number;
};

export default function TransactionsPage() {
  const supabase = createClient();
  const { user: currentUser, isAdmin, loading: authLoading } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 20;

  async function fetchTransactions(currentPage: number) {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    setLoading(true);
    const { data, error } = await supabase.rpc('get_transactions', {
      p_limit: pageSize,
      p_offset: (currentPage - 1) * pageSize,
    });
    
    if (error) {
      toast.error('讀取交易紀錄失敗: ' + error.message);
      setTransactions([]);
    } else if (data && data.length > 0) {
      setTransactions(data);
      setTotalCount(data[0].total_count);
    } else {
      setTransactions([]);
      setTotalCount(0);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (!authLoading && currentUser) {
      fetchTransactions(page);
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [authLoading, currentUser, page]);

  const handleNextPage = () => {
    if (page * pageSize < totalCount) {
      setPage(page + 1);
    }
  };

  const handlePreviousPage = () => {
    if (page > 1) {
      setPage(page - 1);
    }
  };

  if (authLoading || loading) {
    return <div className="p-10 text-center">讀取中...</div>;
  }

  if (!currentUser) {
    return <div className="p-10 text-center text-red-600">權限不足：請先登入</div>;
  }

  return (
    <div className="container mx-auto py-10">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">交易紀錄</h1>
        {/* TODO: Add Date Picker for filtering */}
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>交易單號</TableHead>
              <TableHead>類型</TableHead>
              <TableHead>狀態</TableHead>
              <TableHead>金額</TableHead>
              <TableHead>卡片類型</TableHead>
              <TableHead>交易時間</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {transactions.length > 0 ? (
              transactions.map((tx) => (
                <TableRow key={tx.id}>
                  <TableCell className="font-mono">{tx.tx_no}</TableCell>
                  <TableCell>{tx.tx_type}</TableCell>
                  <TableCell>{tx.status}</TableCell>
                  <TableCell>${tx.final_amount.toLocaleString()}</TableCell>
                  <TableCell>{tx.card_type}</TableCell>
                  <TableCell>{new Date(tx.created_at).toLocaleString()}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-gray-500">
                  沒有交易紀錄
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end space-x-2 py-4">
        <div className="text-sm text-muted-foreground">
          第 {page} 頁，共 {Math.ceil(totalCount / pageSize)} 頁
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePreviousPage}
          disabled={page <= 1}
        >
          上一頁
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleNextPage}
          disabled={page * pageSize >= totalCount}
        >
          下一頁
        </Button>
      </div>
    </div>
  );
}