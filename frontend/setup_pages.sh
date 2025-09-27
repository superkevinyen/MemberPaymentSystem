#!/bin/bash
set -e

# ========================================
# Member Payment System 前端目录初始化脚本（加强版）
# Next.js (App Router) + Tailwind + Supabase
# ========================================

echo "▶️ 创建目录结构..."
mkdir -p "app/(auth)/sign-up"
mkdir -p "app/(user)/dashboard"
mkdir -p "app/(user)/cards"
mkdir -p "app/(user)/qr/[cardId]"
mkdir -p "app/(user)/topup"
mkdir -p "app/(enterprise)/dashboard"
mkdir -p "app/(enterprise)/admin"
mkdir -p "app/(enterprise)/members"
mkdir -p "app/(enterprise)/topup"
mkdir -p "app/(merchant)/dashboard"
mkdir -p "app/(merchant)/charge"
mkdir -p "app/(merchant)/refund"
mkdir -p lib/supabase
mkdir -p hooks

echo "▶️ 生成最小页面（避免空文件编译报错）..."
cat > "app/(auth)/sign-up/page.tsx" <<'TSX'
'use client';
import { useState } from 'react';
import { supabaseBrowser } from '@/lib/supabase/client-browser';

export default function SignUpPage() {
  const sb = supabaseBrowser();
  const [email, setEmail] = useState(''); const [pwd, setPwd] = useState('');
  const [name, setName] = useState('');  const [msg, setMsg] = useState('');
  const submit = async (e:any) => {
    e.preventDefault(); setMsg('');
    const { data: s, error: e1 } = await sb.auth.signUp({ email, password: pwd });
    if (e1) return setMsg(e1.message);
    const uid = s.user?.id; if (!uid) return setMsg('注册失败');
    const { error: e2 } = await sb.from('app.member_profiles').insert({ id: uid, name });
    if (e2) return setMsg(e2.message);
    setMsg('注册成功！已为你创建个人卡。');
  };
  return (
    <form onSubmit={submit} className="p-6 space-y-3 max-w-sm">
      <h1 className="text-xl font-semibold">注册</h1>
      <input className="border rounded-xl px-3 py-2 w-full" placeholder="姓名" value={name} onChange={e=>setName(e.target.value)} />
      <input className="border rounded-xl px-3 py-2 w-full" placeholder="邮箱" value={email} onChange={e=>setEmail(e.target.value)} />
      <input className="border rounded-xl px-3 py-2 w-full" type="password" placeholder="密码" value={pwd} onChange={e=>setPwd(e.target.value)} />
      <button className="px-3 py-2 rounded-xl bg-black text-white">注册</button>
      {msg && <div className="text-sm">{msg}</div>}
    </form>
  );
}
TSX

for f in \
  "app/(user)/dashboard/page.tsx" \
  "app/(user)/cards/page.tsx" \
  "app/(user)/qr/[cardId]/page.tsx" \
  "app/(user)/topup/page.tsx" \
  "app/(enterprise)/dashboard/page.tsx" \
  "app/(enterprise)/admin/page.tsx" \
  "app/(enterprise)/members/page.tsx" \
  "app/(enterprise)/topup/page.tsx" \
  "app/(merchant)/dashboard/page.tsx" \
  "app/(merchant)/charge/page.tsx" \
  "app/(merchant)/refund/page.tsx"
do
  cat > "$f" <<'TSX'
export default function Page() {
  return <div className="p-6">TODO: 实现本页功能（稍后粘贴具体代码）</div>;
}
TSX
done

echo "▶️ 写入 Supabase 工具文件..."
cat > "lib/supabase/client-browser.ts" <<'TS'
import { createClient } from '@supabase/supabase-js';
export function supabaseBrowser() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  if (!url || !anon) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');
  return createClient(url, anon, {
    auth: { persistSession: true, autoRefreshToken: true },
    global: { headers: { 'x-client': 'mps-frontend' } },
  });
}
TS

cat > "lib/supabase/client-server.ts" <<'TS'
// lib/supabase/client-server.ts
import { cookies } from 'next/headers';
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import type { NextRequest, NextResponse } from 'next/server';

/** ① Server Components / SSR：只读 cookie */
export function supabaseServer() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  if (!url || !anon) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');

  const store = cookies();

  return createServerClient(url, anon, {
    cookies: {
      get(name: string): string | undefined {
        const c = (store as any)?.get?.(name);
        return c?.value as string | undefined;
      },
      // set/remove 在 Server Component 场景下通常不可写，这里做 no-op 以兼容类型
      set(name: string, value: string, options?: CookieOptions) {
        try {
          // @ts-expect-error: 在 RSC 场景下不可写，忽略
          store.set({ name, value, ...(options ?? {}) });
        } catch {}
      },
      remove(name: string, options?: CookieOptions) {
        try {
          // @ts-expect-error: 在 RSC 场景下不可写，忽略
          store.set({ name, value: '', ...(options ?? {}), maxAge: 0 });
        } catch {}
      },
    },
  });
}

/** ② Route Handler：读写 cookie（真正需要写入会话时用它） */
export function supabaseServerForRoute(request: NextRequest, response: NextResponse) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  if (!url || !anon) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');

  return createServerClient(url, anon, {
    cookies: {
      get: (name: string) => request.cookies.get(name)?.value,
      set: (name: string, value: string, options?: CookieOptions) => {
        response.cookies.set(name, value, options);
      },
      remove: (name: string, options?: CookieOptions) => {
        response.cookies.set(name, '', { ...options, maxAge: 0 });
      },
    },
  });
}
TS

cat > "lib/supabase/rpc.ts" <<'TS'
import { supabaseBrowser } from './client-browser';
export type RpcArgs = Record<string, any> | undefined;

export async function rpc<T = any>(fn: string, args?: RpcArgs): Promise<T> {
  const sb = supabaseBrowser();
  const { data, error } = await sb.rpc(fn, args ?? {});
  if (error) throw new Error(humanizeError(error));
  const result: any = data;
  if (Array.isArray(result) && result.length === 1) return result[0] as T;
  return result as T;
}

export async function rpcWithIdem<T = any>(fn: string, args?: RpcArgs, key?: string) {
  const idem = key ?? (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`);
  return rpc<T>(fn, { p_idempotency_key: idem, ...(args ?? {}) });
}

function humanizeError(e: { message?: string; details?: string; code?: string }) {
  const raw = (e?.message || e?.details || '').toUpperCase();
  if (raw.includes('QR_EXPIRED')) return '二维码已过期或无效，请刷新后重试';
  if (raw.includes('INSUFFICIENT_BALANCE')) return '余额不足';
  if (raw.includes('ONLY_ENTERPRISE_ADMIN')) return '仅企业管理员可执行此操作';
  if (raw.includes('NOT_MERCHANT_USER')) return '当前账号不是商户成员，无法收款';
  if (raw.includes('IDEMPOTENCY')) return '重复请求：该操作已处理';
  return e?.message || '操作失败，请稍后重试';
}
TS

echo "▶️ 写入通用工具 TS..."
cat > "lib/roles.ts" <<'TS'
export type AppRole = 'member' | 'merchant' | 'enterprise_admin';
export const ROLE = { MEMBER:'member', MERCHANT:'merchant', ENTERPRISE_ADMIN:'enterprise_admin' } as const;
export function hasAnyRole(userRoles: string[], allow: AppRole[]) { return allow.some(r => userRoles.includes(r)); }
TS

cat > "lib/format.ts" <<'TS'
export function fmtCNY(n: number | string, digits = 2) {
  const num = typeof n === 'string' ? Number(n) : n;
  return `¥${(num || 0).toFixed(digits)}`;
}
export function fmtPct(p: number | string, digits = 0) {
  const num = typeof p === 'string' ? Number(p) : p;
  return `${((num || 0) * 100).toFixed(digits)}%`;
}
export function fmtTime(v: string | number | Date) {
  const d = new Date(v);
  return isNaN(d.getTime()) ? '' : d.toLocaleString();
}
export function safeNumber(v: any, def = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : def;
}
TS

cat > "lib/auth.ts" <<'TS'
import { supabaseServer } from './supabase/client-server';
import type { AppRole } from './roles';

export async function getCurrentUser() {
  const sb = supabaseServer();
  const { data: { user } } = await sb.auth.getUser();
  return user;
}
export async function getCurrentUserAndRoles(): Promise<{ user: any; roles: AppRole[] }> {
  const sb = supabaseServer();
  const { data: { user } } = await sb.auth.getUser();
  if (!user) return { user: null, roles: [] };
  // 建议后端提供 rpc: app.my_roles()，这里先兜底为 ['member']
  const roles: AppRole[] = ['member'];
  return { user, roles };
}
TS

echo "▶️ 写入 hooks..."
cat > "hooks/useCountdown.ts" <<'TS'
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
TS

echo "▶️ 写入环境变量类型 (env.d.ts)..."
cat > "env.d.ts" <<'TS'
declare namespace NodeJS {
  interface ProcessEnv {
    NEXT_PUBLIC_SUPABASE_URL: string;
    NEXT_PUBLIC_SUPABASE_ANON_KEY: string;
  }
}
TS

# 安装依赖（可切换 pnpm/yarn）
# 安装依赖 (可切换 pnpm / yarn / npm)
PKG="${1:-npm}"
echo "▶️ 安装依赖 (${PKG})..."

if [ "$PKG" = "pnpm" ]; then
  pnpm add @supabase/supabase-js @supabase/ssr zod react-hook-form qrcode.react @yudiel/react-qr-scanner
elif [ "$PKG" = "yarn" ]; then
  yarn add @supabase/supabase-js @supabase/ssr zod react-hook-form qrcode.react @yudiel/react-qr-scanner
else
  npm i @supabase/supabase-js @supabase/ssr zod react-hook-form qrcode.react @yudiel/react-qr-scanner
fi

echo "✅ 完成！"
echo "请在项目根目录创建 .env.local："
cat <<'ENV'
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOi...
ENV

echo "▶️ 记得在 tsconfig.json 的 include 里加入 env.d.ts，例如："
cat <<'JSON'
{
  "compilerOptions": { "baseUrl": ".", "paths": { "@/*": ["./*"] } },
  "include": ["next-env.d.ts", "env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
JSON
