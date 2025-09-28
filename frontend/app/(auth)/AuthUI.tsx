'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client-browser';
import { toast } from 'react-hot-toast';
import Link from 'next/link';
import { getUserRoles } from '@/lib/roles';

type AuthMode = 'login' | 'signup';
type UserType = 'admin' | 'member';
type MemberLoginMode = 'memberId' | 'phone';

export default function AuthPage({ mode: initialMode }: { mode: 'login' | 'signup' }) {
  const router = useRouter();
  
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [userType, setUserType] = useState<UserType>('admin');
  const [memberLoginMode, setMemberLoginMode] = useState<MemberLoginMode>('memberId');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [memberId, setMemberId] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isLogin = mode === 'login';

  const handleSignUp = async () => {
    const toastId = toast.loading('正在注册...');
    setIsLoading(true);
    const supabase = createClient();
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${process.env.NEXT_PUBLIC_SITE_URL}/auth/callback`,
        },
      });

      if (error) throw error;

      // All signups are for admins now, so no need to check userType.
      // The logic to not create a member profile for admins is implicitly handled
      // by removing the call to handle_new_user.

      toast.success('注册成功！请检查您的邮箱以完成验证。', { id: toastId, duration: 8000 });
      // Clear form or redirect to a page that says "check your email"
      setName('');
      setEmail('');
      setPassword('');
      
    } catch (error: any) {
      console.error('Sign up error:', error);
      toast.error(error.message || '注册时发生未知错误', { id: toastId });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleLogin = async () => {
    const toastId = toast.loading('正在登入...');
    setIsLoading(true);
    const supabase = createClient();

    try {
      let loginEmail = email;
      let userIsAdmin = userType === 'admin';

      // Member login logic
      if (!userIsAdmin) {
        type AuthResponse = { email: string; user_id: string };

        if (memberLoginMode === 'memberId') {
          const { data, error } = await supabase.rpc('authenticate_by_member_no', { p_member_no: memberId }).single<AuthResponse>();
          if (error || !data) throw new Error('會員號不存在或錯誤');
          loginEmail = data.email;
        } else if (memberLoginMode === 'phone') {
          const { data, error } = await supabase.rpc('authenticate_by_phone', { p_phone: phone }).single<AuthResponse>();
          if (error || !data) throw new Error('手機號不存在或錯誤');
          loginEmail = data.email;
        }
      }

      const { data: { user }, error: authError } = await supabase.auth.signInWithPassword({ email: loginEmail, password });
      if (authError || !user) throw authError || new Error('登入失敗，請確認登入資訊');

      toast.success('登入成功！正在為您跳轉...', { id: toastId });

      if (userIsAdmin) {
        router.push('/enterprise/admin/dashboard');
      } else {
        const roles = await getUserRoles(user.id);
        if (roles.includes('merchant_user')) {
          router.push('/merchant/dashboard');
        } else if (roles.includes('enterprise_admin')) {
          router.push('/enterprise/dashboard');
        } else {
          router.push('/user/dashboard');
        }
      }

    } catch (error: any) {
      console.error('Login error:', error);
      toast.error(error.message || '登入時發生未知錯誤', { id: toastId });
    } finally {
      setIsLoading(false);
    }
  };
  
  // ... ( बाकी का component code same रहेगा )
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (isLogin) {
      handleLogin();
    } else {
      handleSignUp();
    }
  };

  const renderLoginFields = () => {
    if (userType === 'admin') {
      return (
        <div>
          <label htmlFor="email" className="text-gray-300">管理員 Email</label>
          <input id="email" type="email" placeholder="admin@example.com" value={email} onChange={e => setEmail(e.target.value)} required className="mt-1 bg-gray-800 text-white border block w-full rounded-md border-gray-600 shadow-sm p-2" />
        </div>
      );
    }

    // Member login fields
    return (
      <div>
        <div className="flex border-b mb-4">
          <button type="button" onClick={() => setMemberLoginMode('memberId')} className={`flex-1 py-2 text-sm ${memberLoginMode === 'memberId' ? 'border-b-2 border-indigo-400 text-white font-semibold' : 'text-gray-400'}`}>會員號</button>
          <button type="button" onClick={() => setMemberLoginMode('phone')} className={`flex-1 py-2 text-sm ${memberLoginMode === 'phone' ? 'border-b-2 border-indigo-400 text-white font-semibold' : 'text-gray-400'}`}>手機號</button>
        </div>
        {memberLoginMode === 'memberId' ? (
          <input id="memberId" type="text" placeholder="會員號" value={memberId} onChange={e => setMemberId(e.target.value)} required className="mt-1 bg-gray-800 text-white border block w-full rounded-md border-gray-600 shadow-sm p-2" />
        ) : (
          <input id="phone" type="tel" placeholder="手機號" value={phone} onChange={e => setPhone(e.target.value)} required className="mt-1 bg-gray-800 text-white border block w-full rounded-md border-gray-600 shadow-sm p-2" />
        )}
      </div>
    );
  }
  
  return (
    <div className="flex justify-center items-center min-h-screen">
      <div className="p-8 space-y-6 border border-gray-700 rounded-lg shadow-lg w-full max-w-sm bg-gray-900">
        <h1 className="text-2xl font-bold text-center text-white">{isLogin ? '登入 MPS 帳戶' : '創建 MPS 帳戶'}</h1>
        
        {isLogin && (
          <div className="flex border-b">
            <button onClick={() => setUserType('admin')} className={`flex-1 py-2 text-sm ${userType === 'admin' ? 'border-b-2 border-indigo-400 text-white font-semibold' : 'text-gray-400'}`}>管理員</button>
            <button onClick={() => setUserType('member')} className={`flex-1 py-2 text-sm ${userType === 'member' ? 'border-b-2 border-indigo-400 text-white font-semibold' : 'text-gray-400'}`}>會員</button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin ? ( // Signup Form
            <>
              <div>
                <label htmlFor="name" className="text-gray-300">姓名</label>
                <input id="name" type="text" placeholder="您的姓名" value={name} onChange={(e) => setName(e.target.value)} required disabled={isLoading} className="mt-1 bg-gray-800 text-white border block w-full rounded-md border-gray-600 shadow-sm p-2" />
              </div>
              <div>
                <label htmlFor="email" className="text-gray-300">Email</label>
                <input id="email" type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required className="mt-1 bg-gray-800 text-white border block w-full rounded-md border-gray-600 shadow-sm p-2" />
              </div>
            </>
          ) : ( // Login Form
            renderLoginFields()
          )}

          <div>
            <label htmlFor="password" className="text-gray-300">密碼</label>
            <input id="password" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} disabled={isLoading} className="mt-1 bg-gray-800 text-white border block w-full rounded-md border-gray-600 shadow-sm p-2" />
          </div>

          <button type="submit" disabled={isLoading} className="w-full flex justify-center py-2 px-4 border rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400">
            {isLoading ? (isLogin ? '登入中...' : '註冊中...') : (isLogin ? '立即登入' : '立即註冊')}
          </button>

          <div className="text-center text-sm">
            {isLogin ? (
              <p>還沒有帳戶？ <Link href="/sign-up" className="font-medium text-indigo-600">立即註冊</Link></p>
            ) : (
              <p>已有帳戶？ <Link href="/login" className="font-medium text-indigo-600">立即登入</Link></p>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}