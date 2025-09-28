# Supabase 整合与 RPC 调用指南

本文档为 MPS 前端项目提供了一套标准的 Supabase 客户 端整合与 RPC 调用模式，旨在确保类型安全、统一的错误处理和代码一致性。

## 1. Supabase Client 创建

项目中已包含分离的客户端创建逻辑，我们将遵循并固化这一实践：

-   **`lib/supabase/client-browser.ts`**: **仅用于客户端组件 (`'use client'`)**。它创建一个单例的 `SupabaseClient` 实例，供整个应用的客户端部分使用。
    ```typescript
    // 示例
    import { createBrowserClient } from '@supabase/ssr'
    export const createClient = () => createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    ```

-   **`lib/supabase/client-server.ts`**: **仅用于服务端组件 (Server Components)、路由处理器 (Route Handlers) 和服务端操作 (Server Actions)**。它利用 `cookies` 来创建一个与当前请求上下文绑定的 `SupabaseClient` 实例。
    ```typescript
    // 示例
    import { createServerClient } from '@supabase/ssr'
    import { cookies } from 'next/headers'
    export const createClient = () => {
        const cookieStore = cookies()
        // ... 创建并返回服务端 client
    }
    ```

## 2. 标准化 RPC 调用封装

直接使用 `supabase.rpc()` 会导致错误处理和 UI 反馈逻辑散落在各个组件中。我们将创建一个统一的辅助函数来封装所有 RPC 调用。

### 2.1 RPC 调用辅助函数 (`lib/supabase/rpc.ts`)

我们将扩展现有的 `rpc.ts`，提供一个名为 `callRpc` 的核心函数。

```typescript
// lib/supabase/rpc.ts
import { createClient } from '@/lib/supabase/client-browser';
import { toast } from 'react-hot-toast'; // 推荐使用 toast 库进行 UI 反馈

// 已经存在的错误转换函数
function humanizeError(message: string): string {
    if (message.includes('QR_EXPIRED_OR_INVALID')) return '二维码已过期或无效，请刷新重试';
    if (message.includes('INSUFFICIENT_BALANCE')) return '账户余额不足';
    // ... 其他错误映射
    return '发生未知错误，请稍后重试';
}

// 定义 RPC 函数名称的类型，利用 Supabase 生成的类型
type RpcFunctionName = keyof Database['public']['Functions'];

// 标准化调用函数
export async function callRpc<T>(
  functionName: RpcFunctionName,
  args: any, // Supabase 的类型定义会自动推断这里的具体类型
  options: { successMessage?: string; autoToast?: boolean } = { autoToast: true }
) {
  const supabase = createClient();
  
  const promise = supabase.rpc(functionName, args);

  if (options.autoToast) {
    toast.promise(promise, {
      loading: '正在处理...',
      success: (response) => {
        if (response.error) throw response.error;
        return options.successMessage ?? '操作成功！';
      },
      error: (err) => humanizeError(err.message),
    });
  }

  const { data, error } = await promise;

  if (error) {
    console.error(`RPC Error (${functionName}):`, error);
    // 这里可以加入更详细的日志记录，如 Sentry
    throw new Error(humanizeError(error.message));
  }

  return data as T;
}

// 针对需要幂等键的 RPC 的便捷封装
export async function callRpcWithIdem<T>(
    functionName: RpcFunctionName,
    args: any,
    options?: { successMessage?: string; autoToast?: boolean }
) {
    const idemArgs = { ...args, p_idempotency_key: crypto.randomUUID() };
    return callRpc<T>(functionName, idemArgs, options);
}
```

### 2.2 使用示例

通过上述封装，组件内的调用将变得极其简洁和标准化。

```typescript
// components/business/ChargePanel.tsx ('use client')
'use client';

import { callRpcWithIdem } from '@/lib/supabase/rpc';
import { useState } from 'react';

export function ChargePanel() {
  const [amount, setAmount] = useState('');
  const [qrCode, setQrCode] = useState('');

  const handleCharge = async () => {
    try {
      const result = await callRpcWithIdem<{
        tx_id: string;
        final_amount: number;
      }>(
        'merchant_charge_by_qr',
        {
          p_merchant_code: 'M001', // 应从用户状态中获取
          p_qr_plain: qrCode,
          p_raw_price: Number(amount),
        },
        { successMessage: `成功收款 ${amount} 元！` }
      );
      
      // 处理成功后的 UI 逻辑，如清空表单
      console.log('Transaction successful:', result.tx_id);
    } catch (e) {
      // 错误已被 toast 自动处理，这里可以处理额外的失败逻辑
      console.error('Charge failed:', (e as Error).message);
    }
  };

  // ... return JSX
}
```

## 3. 类型安全

- **Database Types**: `supabase gen types typescript` 命令会生成 `database.types.ts` 文件，其中包含了所有表、视图、枚举和 **RPC 函数的参数及返回值类型**。
- **强制使用**:
    -   `createClient` 函数应强制使用生成的 `Database` 类型进行泛型约束。
    -   `callRpc` 的 `functionName` 参数应被约束为 `keyof Database['public']['Functions']`。
    -   这将确保在 TypeScript 层面，任何对不存在的 RPC 或错误参数的调用都会被捕捉到。

通过实施这份指南，我们可以确保前端与 Supabase 的交互是类型安全、可维护且用户体验友好的。