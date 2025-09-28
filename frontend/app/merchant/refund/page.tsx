"use client";

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from 'react-hot-toast';

export default function RefundPage() {
  const supabase = createClient();
  
  const [merchantCode, setMerchantCode] = useState('');
  const [originalTxNo, setOriginalTxNo] = useState('');
  const [refundAmount, setRefundAmount] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRefund = async () => {
    if (!merchantCode || !originalTxNo || !refundAmount) {
      toast.error('商家代碼、原始交易單號和退款金額為必填項。');
      return;
    }

    setLoading(true);
    const toastId = toast.loading('正在處理退款...');

    const { data, error } = await supabase.rpc('merchant_refund_tx', {
      p_merchant_code: merchantCode,
      p_original_tx_no: originalTxNo,
      p_refund_amount: parseFloat(refundAmount),
    });

    if (error) {
      toast.error(`退款失敗: ${error.message}`, { id: toastId });
    } else {
      toast.success(
        (t) => (
          <div className="flex flex-col">
            <b>退款成功！</b>
            <span>退款單號: {data[0].refund_tx_no}</span>
            <span>退款金額: ${data[0].refunded_amount.toLocaleString()}</span>
          </div>
        ),
        { id: toastId, duration: 6000 }
      );
      // Reset form
      setOriginalTxNo('');
      setRefundAmount('');
    }
    setLoading(false);
  };

  return (
    <div className="container mx-auto py-10 flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>商家退款</CardTitle>
          <CardDescription>輸入原始交易單號和金額以處理退款。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid w-full items-center gap-4">
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="merchant-code">商家代碼</Label>
              <Input 
                id="merchant-code" 
                placeholder="您的商家代碼" 
                value={merchantCode}
                onChange={(e) => setMerchantCode(e.target.value)}
              />
            </div>
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="tx-no">原始交易單號</Label>
              <Input 
                id="tx-no" 
                placeholder="例如: ZF123456" 
                value={originalTxNo}
                onChange={(e) => setOriginalTxNo(e.target.value)}
              />
            </div>
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="amount">退款金額</Label>
              <Input 
                id="amount" 
                type="number" 
                placeholder="例如: 50.00" 
                value={refundAmount}
                onChange={(e) => setRefundAmount(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={handleRefund} disabled={loading} className="w-full">
            {loading ? '處理中...' : '確認退款'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
