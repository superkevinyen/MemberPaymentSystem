import { createClient } from './supabase/client-server';
import type { AppRole } from './roles';
import { cookies } from 'next/headers';

export async function getCurrentUser() {
  const cookieStore = cookies();
  const sb = createClient(cookieStore);
  const { data: { user } } = await sb.auth.getUser();
  return user;
}
export async function getCurrentUserAndRoles(): Promise<{ user: any; roles: AppRole[] }> {
  const cookieStore = cookies();
  const sb = createClient(cookieStore);
  const { data: { user } } = await sb.auth.getUser();
  if (!user) return { user: null, roles: [] };
  // 建议后端提供 rpc: app.my_roles()，这里先兜底为 ['member']
  const roles: AppRole[] = ['member'];
  return { user, roles };
}
