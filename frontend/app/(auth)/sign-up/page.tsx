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
