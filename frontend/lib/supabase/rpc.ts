import { createClient } from './client-browser';
import { toast } from 'react-hot-toast';

// TODO: 1. 执行 `npx supabase gen types typescript --project-id <your-project-id> > frontend/lib/supabase/database.types.ts`
// TODO: 2. 取消下面的注释, 并将 RpcFunctionName = string 替换掉
// import { Database } from './database.types';
// type RpcFunctionName = keyof Database['public']['Functions'];

// 在 database.types.ts 文件生成前的临时方案
type RpcFunctionName = string;

export type RpcArgs = Record<string, any> | undefined;

// 标准化的 RPC 调用函数 (手动 Toast 版本)
export async function callRpc<T>(
  functionName: RpcFunctionName,
  args?: RpcArgs,
  options: { successMessage?: string; loadingMessage?: string; autoToast?: boolean } = { autoToast: true }
) {
  const supabase = createClient();
  let toastId: string | undefined;

  if (options.autoToast) {
    toastId = toast.loading(options.loadingMessage ?? '正在处理...');
  }

  try {
    const { data, error } = await supabase.rpc(String(functionName), args);

    if (error) {
      throw error; // 交给 catch 块处理
    }

    if (options.autoToast && toastId) {
      toast.success(options.successMessage ?? '操作成功！', { id: toastId });
    }
    
    const result: any = data;
    if (Array.isArray(result) && result.length === 1) return result[0] as T;
    return result as T;

  } catch (error: any) {
    console.error(`RPC Error (${String(functionName)}):`, error);
    if (options.autoToast && toastId) {
      toast.error(humanizeError(error), { id: toastId });
    }
    // 重新抛出错误，以便调用方可以进行额外的处理
    throw new Error(humanizeError(error));
  }
}

// 针对需要幂等键的 RPC 的便捷封装
export async function callRpcWithIdem<T>(
    functionName: RpcFunctionName,
    args?: RpcArgs,
    options?: { successMessage?: string; autoToast?: boolean }
) {
    const idemArgs = { p_idempotency_key: crypto.randomUUID(), ...args };
    return callRpc<T>(functionName, idemArgs, options);
}

// 增强的错误处理函数
function humanizeError(e: { message?: string; details?: string; code?: string }): string {
  const raw = (e?.message || e?.details || '').toUpperCase();
  if (raw.includes('QR_EXPIRED')) return '二维码已过期或无效，请刷新后重试';
  if (raw.includes('INSUFFICIENT_BALANCE')) return '余额不足';
  if (raw.includes('ONLY_ENTERPRISE_ADMIN')) return '仅企业管理员可执行此操作';
  if (raw.includes('NOT_MERCHANT_USER')) return '当前账号不是商户成员，无法收款';
  if (raw.includes('IDEMPOTENCY')) return '重复请求：该操作已处理';
  if (raw.includes('INVALID_CARD_PASSWORD')) return '企业卡密码错误';
  if (raw.includes('ONLY_COMPLETED_PAYMENT_REFUNDABLE')) return '只有已完成的支付才能退款';
  if (raw.includes('REFUND_EXCEEDS_REMAINING')) return '退款金额超过可退款上限';

  return e?.message || '操作失败，请稍后重试';
}
