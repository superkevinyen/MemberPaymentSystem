import { useEffect, useState } from 'react';

export const useCountdown = (targetDate: string | null) => {
  const countDownDate = targetDate ? new Date(targetDate).getTime() : null;

  const [countDown, setCountDown] = useState(
    countDownDate ? countDownDate - new Date().getTime() : 0
  );

  useEffect(() => {
    if (!countDownDate) {
      setCountDown(0);
      return;
    }

    const interval = setInterval(() => {
      const newCountDown = countDownDate - new Date().getTime();
      setCountDown(newCountDown > 0 ? newCountDown : 0);
    }, 1000);

    return () => clearInterval(interval);
  }, [countDownDate]);

  const secondsLeft = Math.floor((countDown / 1000) % 60);
  const minutesLeft = Math.floor((countDown / (1000 * 60)) % 60);

  return { 
    minutes: minutesLeft, 
    seconds: secondsLeft, 
    secondsLeft: Math.floor(countDown / 1000),
    isExpired: countDown <= 0,
  };
};
