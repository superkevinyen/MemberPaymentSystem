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
