"use client";

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from 'react-hot-toast';

export default function ChargePage() {
  const supabase = createClient();
  
  const [merchantCode, setMerchantCode] = useState('');
  const [qrPlain, setQrPlain] = useState('');
  const [rawPrice, setRawPrice] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCharge = async () => {
    if (!merchantCode || !qrPlain || !rawPrice) {
      toast.error('商家代碼、QR Code和金額為必填項。');
      return;
    }

    setLoading(true);
    const toastId = toast.loading('正在處理收款...');

    const { data, error } = await supabase.rpc('merchant_charge_by_qr', {
      p_merchant_code: merchantCode,
      p_qr_plain: qrPlain,
      p_raw_price: parseFloat(rawPrice),
    });

    if (error) {
      toast.error(`收款失敗: ${error.message}`, { id: toastId });
    } else {
      toast.success(
        (t) => (
          <div className="flex flex-col">
            <b>收款成功！</b>
            <span>交易單號: {data[0].tx_no}</span>
            <span>最終金額: ${data[0].final_amount.toLocaleString()}</span>
          </div>
        ),
        { id: toastId, duration: 6000 }
      );
      // Reset form
      setQrPlain('');
      setRawPrice('');
    }
    setLoading(false);
  };

  return (
    <div className="container mx-auto py-10 flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>商家收款</CardTitle>
          <CardDescription>輸入顧客的 QR Code 和消費金額以完成交易。</CardDescription>
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
              <Label htmlFor="qr-plain">顧客 QR Code</Label>
              <Input 
                id="qr-plain" 
                placeholder="掃描或輸入的 QR Code 內容" 
                value={qrPlain}
                onChange={(e) => setQrPlain(e.target.value)}
              />
            </div>
            <div className="flex flex-col space-y-1.5">
              <Label htmlFor="price">消費金額</Label>
              <Input 
                id="price" 
                type="number" 
                placeholder="例如: 150.00" 
                value={rawPrice}
                onChange={(e) => setRawPrice(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={handleCharge} disabled={loading} className="w-full">
            {loading ? '處理中...' : '確認收款'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
