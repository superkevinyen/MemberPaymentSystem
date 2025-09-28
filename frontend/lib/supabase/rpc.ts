import { createClient } from '@/lib/supabase/client';
import { toast } from 'react-hot-toast';
import { Database } from '@/lib/database.types';

type RpcName = keyof Database['public']['Functions'];

// A generic wrapper for calling Supabase RPCs with consistent error handling and toast notifications.
export async function callRpc<T extends RpcName>(
  name: T,
  args: Database['public']['Functions'][T]['Args']
): Promise<Database['public']['Functions'][T]['Returns']> {
  const supabase = createClient();
  const { data, error } = await supabase.rpc(name, args);

  if (error) {
    console.error(`RPC call to '${String(name)}' failed:`, error);
    toast.error(`操作失敗: ${error.message}`);
    throw error;
  }

  return data as Database['public']['Functions'][T]['Returns'];
}

// Example of how you might use this in a component:
/*
import { callRpc } from '@/lib/supabase/rpc';

async function handleSomeAction(userId: string) {
  try {
    const result = await callRpc('admin_update_user_metadata', {
      p_user_id: userId,
      p_metadata: { is_admin: true },
    });
    toast.success('用戶權限已更新！');
  } catch (e) {
    // Error is already logged and toasted by callRpc
  }
}
*/
