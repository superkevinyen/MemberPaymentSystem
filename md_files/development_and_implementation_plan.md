# MPS 前端开发与实施计画

## 1. 项目总览与目标

本项目旨在使用 Next.js 和 Supabase 构建一个功能完善的会员支付系统 (MPS) 前端。项目目标是实现一个安全、可靠且用户体验良好的 Web 应用，支持会员、企业管理员和商户三种核心角色。

架构遵循以后端 RPC 为业务逻辑核心、前端负责 UI 展示与交互的模式。具体的架构设计、角色权限、组件规划等已在以下先行文档中详细定义：
- `architecture.md`
- `roles_and_permissions.md`
- `frontend_structure_plan.md`
- `data_flow_and_state_management.md`
- `supabase_integration_guide.md`

## 2. 开发前提条件

在前端开发正式启动前，需确保以下后端条件已满足：
1.  **数据库脚本**: `mps_full.sql` 已在目标 Supabase 项目中**分段并成功**执行完毕。
2.  **类型生成**: 已执行 `npx supabase gen types typescript` 命令，生成了最新的 `database.types.ts` 文件。
3.  **环境变量**: 前端项目根目录下的 `.env.local` 文件已正确配置 `NEXT_PUBLIC_SUPABASE_URL` 和 `NEXT_PUBLIC_SUPABASE_ANON_KEY`。

## 3. 开发里程碑与冲刺 (Sprint) 规划

我们将开发过程划分为三个核心里程碑，每个历时约 1-2 周。

### 里程碑 1 (M1): 会员核心闭环 (预计 1 周)
**目标**: 实现普通会员从注册到支付的完整核心流程。

| 任务 (Task) | 涉及页面/组件 | 核心 RPCs | 验收标准 |
| :--- | :--- | :--- | :--- |
| **M1.1**: 用户认证 | `/(auth)/*`, `AuthForm` | `supabase.auth` | 用户可以成功注册和登录，注册后自动获得个人卡。 |
| **M1.2**: 会员仪表盘 | `/(user)/dashboard` | `v_user_cards`, `v_usage_logs` | 登录后可看到卡片余额、积分和最近交易。 |
| **M1.3**: 出示二维码 | `/(user)/qr/[cardId]` | `rotate_card_qr` | 用户可以选择卡片并生成一个带 15 分钟倒计时的动态二维码。 |
| **M1.4**: 个人储值 | `/(user)/topup` | `user_recharge_personal_card` | 用户可以为自己的个人卡储值，余额实时更新。 |
| **M1.5**: 基础库封装 | `lib/supabase/rpc.ts` | N/A | `callRpc` 和 `callRpcWithIdem` 辅助函数按指南实现。 |

### 里程碑 2 (M2): 商户功能闭环 (预计 1 周)
**目标**: 实现商户用户的收款与退款功能。

| 任务 (Task) | 涉及页面/组件 | 核心 RPCs | 验收标准 |
| :--- | :--- | :--- | :--- |
| **M2.1**: 商户角色识别 | `(merchant)/layout.tsx` | (需角色查询逻辑) | 商户用户登录后被正确引导至商户仪表盘。 |
| **M2.2**: 扫码收款 | `/(merchant)/charge`, `QrScanner` | `merchant_charge_by_qr` | 商户可以输入金额，并通过摄像头扫描会员二维码完成收款。 |
| **M2.3**: 交易退款 | `/(merchant)/refund` | `merchant_refund_tx` | 商户可以根据原交易号进行部分或全额退款。 |
| **M2.4**: 商户交易查询 | `/(merchant)/dashboard` | `v_usage_logs` | 商户可以查看本店相关的交易流水。 |

### 里程碑 3 (M3): 企业管理功能 (预计 1 周)
**目标**: 完成企业管理员对企业卡和成员的管理功能。

| 任务 (Task) | 涉及页面/组件 | 核心 RPCs | 验收标准 |
| :--- | :--- | :--- | :--- |
| **M3.1**: 企业管理员识别 | `(enterprise)/layout.tsx` | (需角色查询逻辑) | 企业管理员登录后可访问企业管理相关页面。 |
| **M3.2**: 成员管理 | `/(enterprise)/members` | `enterprise_add_member`, `enterprise_remove_member` | 管理员可以添加和移除企业卡绑定的成员。 |
| **M3.3**: 企业卡储值 | `/(enterprise)/topup` | `user_recharge_enterprise_card_admin` | 管理员可以为企业卡进行储值。 |
| **M3.4**: 初始管理员设置 | `/(enterprise)/admin` | `enterprise_set_initial_admin` | 提供一个一次性界面用于设置企业卡的初始管理员。 |

## 4. 协作与代码质量

1.  **遵循设计文档**: 所有开发工作应严格遵循本系列规划文档。
2.  **组件化开发**: 优先开发 `frontend/components/ui/` 和 `frontend/components/business/` 中的可复用组件。
3.  **统一 RPC 调用**: 所有对后端的写操作**必须**通过 `lib/supabase/rpc.ts` 中封装的 `callRpc` 或 `callRpcWithIdem` 函数进行。
4.  **代码规范**: 遵循项目已配置的 ESLint 和 Prettier 规则。
5.  **提交信息**: 遵循 Conventional Commits 规范 (e.g., `feat(user): implement QR code display page`)。

## 5. 下一步行动

这份计画已经全面覆盖了前端从 0 到 1 的实施路径。我已经完成了对您需求的分析和架构设计。

**我建议下一步切换到“代码”模式，并从里程碑 1 (M1) 的第一个任务开始，着手进行具体的编码实现。**