# 前端页面与组件结构规划

本文档基于现有项目结构和需求文档，旨在为 Member Payment System (MPS) 的前端开发提供一份详细的页面与组件设计蓝图。

## 1. 目录结构与布局 (Layouts)

我们将沿用并扩展现有的基于角色的路由分组结构。每个路由组将拥有自己的 `layout.tsx`，用于处理该角色通用的 UI 布局和数据获取逻辑。

```
frontend/app/
├── (auth)/layout.tsx        # 认证页面的居中、简洁布局
├── (auth)/sign-up/page.tsx
│
├── (user)/layout.tsx        # 会员专区布局 (如带“我的卡片”、“储值”等导航)
├── (user)/dashboard/page.tsx
├── (user)/cards/page.tsx
├── ...
│
├── (enterprise)/layout.tsx  # 企业管理员布局 (包含会员布局，并增加“成员管理”等导航)
├── (enterprise)/members/page.tsx
├── ...
│
├── (merchant)/layout.tsx    # 商户布局 (包含“收款”、“退款”等导航)
├── (merchant)/charge/page.tsx
├── ...
│
└── layout.tsx               # 全局根布局 (包含 Supabase session provider, Toaster 等)
```

## 2. 页面 (Pages) 核心职责

每个 `page.tsx` 应该专注于展示特定路由的内容，并处理该页面的核心业务逻辑。数据获取建议通过 Server Components 实现，而交互逻辑则放在 Client Components 中。

| 页面路由 | 核心职责 | 组件构成 (示例) |
| :--- | :--- | :--- |
| **(user)/dashboard** | 显示用户个人卡和企业卡的余额、积分、等级汇总，以及最近交易列表。 | `UserDashboard` (Client), `CardSummary` (Server), `RecentTransactions` (Server) |
| **(user)/cards** | 列表展示用户所有卡片 (个人/企业)，并提供入口跳转至详情或二维码页面。 | `CardList` (Client), `CardItem` (Server) |
| **(user)/qr/[cardId]** | 生成并显示指定卡片的动态二维码，包含过期倒计时。 | `QrCodeDisplay` (Client), `CountdownTimer` (Client) |
| **(user)/topup** | 提供个人卡储值表单。 | `TopupForm` (Client), `PaymentMethodSelector` (Client) |
| **(enterprise)/members** | (管理员) 展示企业卡成员列表，提供添加/移除成员的操作入口。 | `MemberList` (Client), `AddMemberModal` (Client), `RemoveMemberButton` (Client) |
| **(merchant)/charge** | (商户) 提供金额输入框和扫码功能，用于向会员收款。 | `ChargePanel` (Client), `AmountInput` (Client), `QrScanner` (Client) |
| **(merchant)/refund** | (商户) 提供表单用以输入原交易号和退款金额，执行退款操作。 | `RefundForm` (Client) |

## 3. 可复用组件 (Reusable Components) 规划

为了提高代码复用率和维护性，我们需要抽离出一系列通用的 UI 和业务组件。建议创建 `frontend/components/` 目录进行存放。

### 3.1 UI 基础组件 (`frontend/components/ui/`)

| 组件名 | 描述 |
| :--- | :--- |
| `Button` | 通用按钮，支持不同状态 (primary, secondary, disabled, loading)。 |
| `Input` | 封装了样式和标签的输入框。 |
| `Card` | 卡片式容器，用于包裹内容块。 |
| `Modal` | 模态对话框，用于弹出表单或确认信息。 |
| `Spinner` | 加载指示器。 |
| `Alert` | 用于显示成功、错误、警告等信息。 |
| `Tabs` | 标签页切换组件。 |
| `Countdown` | 倒计时组件。|
| `QRCode` | 二维码组件。|

### 3.2 业务逻辑组件 (`frontend/components/business/`)

| 组件名 | 描述 | 引入页面 |
| :--- | :--- | :--- |
| `UserCardDisplay` | 统一的会员卡/企业卡样式展示组件，显示卡号、余额、等级/折扣等。 | `(user)/dashboard`, `(user)/cards` |
| `TransactionList` | 交易列表组件，可配置数据源 (个人交易/商户交易)。 | `(user)/dashboard`, `(merchant)/dashboard` |
| `QrCodePanel` | 封装了调用 `rotate_card_qr` RPC、显示二维码及倒计时的完整逻辑。 | `(user)/qr/[cardId]` |
| `RoleBasedGuard` | 客户端组件，用于检查用户角色并根据权限决定是否渲染子组件或重定向。 | 各角色 `layout.tsx` |
| `TopupForm` | 储值表单，处理金额输入、支付方式选择和 RPC 调用。 | `(user)/topup`, `(enterprise)/topup` |
| `QrScanner` | 封装了 `@yudiel/react-qr-scanner`，处理扫码逻辑并返回解码后的文本。 | `(merchant)/charge` |
| `AddEnterpriseMemberForm` | 添加企业成员的表单，包含输入卡密码和调用 RPC 的逻辑。 | `(enterprise)/members` |

## 4. 数据流与状态管理

详见下一步 `设计状态管理与数据流策略`。总体原则是：
*   **Server Components 优先**: 尽可能在服务端组件中直接从 Supabase 获取页面初始化所需的数据。
*   **Client Components 用于交互**: 客户端组件负责处理用户交互、表单状态和执行 RPC 调用。
*   **轻量级状态管理**: 仅对全局共享且需频繁更新的状态（如用户信息）考虑使用全局状态管理方案。

这份规划为前端开发提供了明确的结构指导。下一步，我们将细化数据流和状态管理策略。