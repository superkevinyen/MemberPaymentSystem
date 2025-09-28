import { createClient } from '@/lib/supabase/client-browser';

export type AppRole = 'member' | 'platform_admin' | 'enterprise_admin' | 'merchant_user';

export const getUserRoles = async (userId: string) => {
  const supabase = createClient();
  const roles = new Set<string>();

  const { data: memberProfile, error: profileError } = await supabase
    .from('member_profiles')
    .select('id')
    .eq('id', userId)
    .single();

  if (!memberProfile) {
    // If a user has an auth entry but no member_profile, they are a platform admin.
    roles.add('platform_admin');
  } else {
    // Everyone with a profile is at least a member
    roles.add('member');
  }

  const { data: enterpriseAdmin, error: enterpriseError } = await supabase
    .from('enterprise_card_bindings')
    .select('role')
    .eq('member_id', userId)
    .eq('role', 'admin')
    .single();

  if (enterpriseAdmin) {
    roles.add('enterprise_admin');
  }

  const { data: merchantUser, error: merchantError } = await supabase
    .from('merchant_users')
    .select('user_id')
    .eq('user_id', userId)
    .single();
  
  if (merchantUser) {
    roles.add('merchant_user');
  }

  return Array.from(roles);
};
