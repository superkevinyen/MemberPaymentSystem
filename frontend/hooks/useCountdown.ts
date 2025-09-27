'use client';
import { useEffect, useState } from 'react';
export default function useCountdown(expires: string | null) {
  const [left, setLeft] = useState<number>(0);
  useEffect(() => {
    if (!expires) return;
    const end = new Date(expires).getTime();
    const tick = () => setLeft(Math.max(0, Math.floor((end - Date.now()) / 1000)));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [expires]);
  return left;
}
