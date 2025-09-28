import { createClient } from '@/lib/supabase/client';

export type AppRole = 'member' | 'platform_admin' | 'enterprise_admin' | 'merchant_user';

export const isPlatformAdmin = async (userId: string): Promise<boolean> => {
  const supabase = createClient();
  const { data, error } = await supabase.rpc('is_admin');
  
  console.log('isPlatformAdmin - userId:', userId);
  console.log('isPlatformAdmin - RPC result:', { data, error });
  
  if (error) {
    console.error('Error checking admin status:', error);
    return false;
  }
  
  return data || false;
};

export const getUserRoles = async (userId: string): Promise<string[]> => {
  const supabase = createClient();
  const roles: string[] = [];
  
  try {
    // 使用新的 get_user_type 函數來獲取用戶類型
    const { data: userType, error } = await supabase.rpc('get_user_type');
    
    if (error) {
      console.error('Error getting user type:', error);
      return ['member']; // 預設為會員
    }
    
    console.log('getUserRoles - userType:', userType);
    
    if (userType === 'platform_admin') {
      roles.push('platform_admin');
    } else if (userType === 'member') {
      roles.push('member');
    }
    
  } catch (error) {
    console.error('Error getting user roles:', error);
    return ['member'];
  }
  
  return roles.length > 0 ? roles : ['member'];
};
