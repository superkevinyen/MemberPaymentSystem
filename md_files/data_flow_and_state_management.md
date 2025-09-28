# 数据流与状态管理策略

本文档为 Member Payment System (MPS) 前端项目定义了数据流和状态管理的核心策略，旨在最大化利用 Next.js App Router 的能力，实现性能与开发效率的最佳平衡。

## 1. 核心原则

1.  **服务端优先 (Server First)**: 尽可能在服务端组件 (Server Components) 中获取和渲染数据。这减少了客户端的负担，利用了 Next.js 的缓存机制，并提升了初始加载性能。
2.  **最小化客户端状态 (Minimize Client-side State)**: 仅在必要时使用客户端状态。大多数“状态”应源自服务端数据或 URL。
3.  **URL 作为状态源 (URL as a Source of Truth)**: 对于页面级的状态，如筛选条件、分页、当前选中的 Tab 等，应优先使用 URL 查询参数 (`URLSearchParams`) 来管理。这使得状态可以被收藏、分享，并且在刷新后保持一致。
4.  **按需选择状态管理工具**: 避免过度设计。从最简单的 `useState` 开始，仅在确实需要在多个组件间共享**交互式**状态时，才引入全局状态管理。

## 2. 状态分类与管理方案

我们将状态分为三类：

### 2.1 服务端状态 (Server State)

-   **定义**: 从 Supabase 数据库中获取的数据，如用户信息、卡片列表、交易记录等。
-   **管理方式**:
    -   **Server Components**: 在服务组件中，通过创建的服务端 Supabase Client 直接调用 `.from(...).select()` 或 `.rpc()`。
    -   **Next.js 缓存**: Next.js 自动缓存 `fetch` 请求。对于 Supabase，可以通过自定义 `fetch` 来利用这一特性，或依赖其自身的缓存策略。`revalidatePath` 和 `revalidateTag` 将用于在数据更新后主动使缓存失效。
-   **示例**:
    ```typescript
    // app/(user)/dashboard/page.tsx (Server Component)
    import { createClient } from '@/lib/supabase/client-server';
    
    export default async function DashboardPage() {
      const supabase = createClient();
      const { data: cards } = await supabase.from('v_user_cards').select('*');
      // ... 直接将 cards 数据传递给子组件
      return <UserDashboard initialCards={cards} />;
    }
    ```

### 2.2 客户端本地状态 (Local Client State)

-   **定义**: 仅限于单个组件内部的、用于处理 UI 交互的状态，如表单输入、模态框的开关状态、下拉菜单的选中项等。
-   **管理方式**:
    -   **`useState` / `useReducer`**: 使用 React 内置的 Hooks 来管理。
-   **示例**:
    ```typescript
    // components/business/TopupForm.tsx ('use client')
    'use client';
    import { useState } from 'react';
    
    export function TopupForm() {
      const [amount, setAmount] = useState('');
      const [isLoading, setIsLoading] = useState(false);
      // ... 处理表单提交
    }
    ```

### 2.3 客户端全局状态 (Global Client State)

-   **定义**: 需要在多个**客户端组件**之间共享的、并且会随用户交互而改变的状态。
-   **识别**: 在本项目中，唯一明确需要全局管理的是 **当前登录的用户信息 (Session/User) 及其派生出的角色信息**。虽然可以在根布局 `layout.tsx` 通过 Server Component 获取并逐层传递，但这会导致繁琐的 props drilling。
-   **管理方式**:
    -   **推荐方案: Zustand**: 鉴于其轻量、简单、无 boilerplate 的特性，推荐使用 Zustand 来创建一个 `useUserStore`。
    -   **替代方案: React Context**: 也可以使用 React Context API，结合 `useState` 或 `useReducer` 来实现。
-   **Zustand 示例**:
    ```typescript
    // lib/store/user.ts
    import { create } from 'zustand';
    import type { User } from '@supabase/supabase-js';

    interface UserState {
      user: User | null;
      roles: string[]; // e.g., ['enterprise_admin', 'merchant_user']
      setUser: (user: User | null) => void;
      setRoles: (roles: string[]) => void;
    }

    export const useUserStore = create<UserState>((set) => ({
      user: null,
      roles: [],
      setUser: (user) => set({ user }),
      setRoles: (roles) => set({ roles }),
    }));
    ```
    -   在根布局的客户端组件中初始化并监听 Supabase 的 `onAuthStateChange`，然后更新这个 store。

## 3. 数据流 (Data Flow)

1.  **初始加载**:
    -   用户访问页面，Next.js 在服务端渲染 Server Components。
    -   根 `layout.tsx` (Server) 获取当前用户 session。
    -   页面级 `page.tsx` (Server) 获取该页面所需的核心数据。
    -   数据作为 props 传递给客户端组件进行水合 (hydration)。
2.  **客户端交互 (写操作)**:
    -   用户在客户端组件中执行操作 (如提交表单)。
    -   组件调用封装好的 Supabase RPC 函数。
    -   RPC 调用成功后，使用 Next.js 的 `router.refresh()` 来重新获取服务端数据并更新UI。这会自动刷新 Server Components 并保持数据同步，是 App Router 推荐的数据更新模式。
3.  **全局状态同步**:
    -   在根布局中设置一个 `SessionProvider` (Client Component)，它负责监听 `supabase.auth.onAuthStateChange`。
    -   当认证状态变化时（登录/登出），更新 `useUserStore` 中的用户信息。
    -   所有订阅了 `useUserStore` 的组件都会自动重新渲染。

通过这种策略，我们最大限度地利用了服务端的渲染能力，同时为必要的客户端交互提供了清晰、可预测且高效的状态管理方案。