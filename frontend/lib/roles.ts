import { createClient } from '@/lib/supabase/client';
import { callRpc } from './supabase/rpc';

export type AppRole = 'member' | 'platform_admin' | 'enterprise_admin' | 'merchant_user';

export const getUserRoles = async (userId: string): Promise<string[]> => {
  const roles = await callRpc('get_user_role', { p_user_id: userId });
  return roles || [];
};

export const isPlatformAdmin = async (userId: string): Promise<boolean> => {
  const roles = await getUserRoles(userId);
  return roles.includes('platform_admin');
};
