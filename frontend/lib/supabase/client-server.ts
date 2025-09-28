// lib/supabase/client-server.ts
import { cookies } from 'next/headers';
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import type { NextRequest, NextResponse } from 'next/server';

/** ① Server Components / SSR：只读 cookie */
export function createClient(store: ReturnType<typeof cookies>) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  if (!url || !anon) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');

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
