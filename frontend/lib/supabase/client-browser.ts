import { createClient as createSupabaseClient } from '@supabase/supabase-js';

// TODO: Replace `any` with `Database` type from `database.types.ts` once it's generated
export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  if (!url || !anon) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY');
  return createSupabaseClient<any>(url, anon, {
    auth: { persistSession: true, autoRefreshToken: true },
    global: { headers: { 'x-client': 'mps-frontend' } },
  });
}
