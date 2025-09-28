// 簡單的測試腳本來檢查管理員權限
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('請設置 SUPABASE_URL 和 SUPABASE_ANON_KEY 環境變量');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function testAdminFunctions() {
  try {
    console.log('測試 get_all_users_for_admin 函數...');
    const { data, error } = await supabase.rpc('get_all_users_for_admin');
    
    if (error) {
      console.error('錯誤:', error);
    } else {
      console.log('成功:', data);
    }
  } catch (err) {
    console.error('異常:', err);
  }
}

testAdminFunctions();