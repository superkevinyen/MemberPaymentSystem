'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client-browser';
import { toast } from 'react-hot-toast';

export default function SignUpPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);

    const toastId = toast.loading('正在注册...');
    const supabase = createClient();

    try {
      // 1. 使用 Supabase Auth 注册用户
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
      });
      if (authError) throw authError;
      if (!authData.user) throw new Error('注册失败，未返回用户信息');

      // 2. 注册成功后，插入会员档案 (将触发数据库自动发卡)
      const { error: profileError } = await supabase
        .from('member_profiles') // 注意：supabase-js v2 RLS 下，表名不需要 schema
        .insert({
          id: authData.user.id,
          name: name,
        });
      if (profileError) throw profileError;

      toast.success('注册成功！已为您自动创建个人会员卡。', { id: toastId });

      // 3. 注册完成，短暂延迟后跳转到用户仪表盘
      setTimeout(() => {
        router.push('/user/dashboard');
      }, 1500);

    } catch (error: any) {
      console.error('Sign up error:', error);
      toast.error(error.message || '注册时发生未知错误', { id: toastId });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center h-full">
      <form onSubmit={handleSubmit} className="p-8 space-y-4 border rounded-lg shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center">创建您的 MPS 账户</h1>

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
            姓名
          </label>
          <input
            id="name"
            type="text"
            className="mt-1 border block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
            placeholder="您的姓名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            邮箱地址
          </label>
          <input
            id="email"
            type="email"
            className="mt-1 border block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="password"className="block text-sm font-medium text-gray-700">
            密码
          </label>
          <input
            id="password"
            type="password"
            className="mt-1 border block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
        >
          {isLoading ? '注册中...' : '立即注册'}
        </button>
      </form>
    </div>
  );
}
