'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

export default function AuthCallback() {
  const router = useRouter();
  const [message, setMessage] = useState('正在驗證您的帳戶...');

  useEffect(() => {
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session && session.access_token) {
        setMessage('驗證成功！正在為您跳轉...');
        setTimeout(() => {
          router.push('/login');
        }, 2000);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  return (
    <div className="flex justify-center items-center min-h-screen">
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold">{message}</h1>
      </div>
    </div>
  );
}