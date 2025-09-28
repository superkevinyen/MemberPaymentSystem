# 角色与权限定义 (Roles and Permissions)

本文档旨在详细说明会员支付系统 (MPS) 中每个用户角色的具体职能和访问权限。

## 角色-权限矩阵

| 角色 (Role) | 描述 (Description) | 可访问的前端路由 (Accessible Frontend Routes) | 可调用的核心 RPCs (Key RPCs) | 数据读取权限 (Data Read Permissions via RLS) |
| :--- | :--- | :--- | :--- | :--- |
| **会员 (Member)** | 系统的标准终端用户，通过 Supabase Auth 进行认证。新注册用户会自动获得一张个人卡。 | `/(auth)/*`<br/>`/(user)/dashboard`<br/>`/(user)/cards`<br/>`/(user)/qr/[cardId]`<br/>`/(user)/topup` | `rotate_card_qr` (自己的卡)<br/>`user_recharge_personal_card`<br/>`enterprise_remove_member` (自解绑) | 只能读取自己的 `member_profiles`、`personal_cards`、绑定的 `enterprise_cards` 及相关的 `transactions` 和 `point_ledger`。 |
| **企业管理员 (Enterprise Admin)** | 企业卡的管理者。除了拥有普通会员的所有权限外，还可以管理企业卡及其成员。 | `/(auth)/*`<br/>`/(user)/*` (作为普通成员)<br/>`/(enterprise)/dashboard`<br/>`/(enterprise)/admin`<br/>`/(enterprise)/members`<br/>`/(enterprise)/topup` | `rotate_card_qr` (企业卡)<br/>`enterprise_set_initial_admin`<br/>`enterprise_add_member`<br/>`enterprise_remove_member`<br/>`user_recharge_enterprise_card_admin` | 除了会员权限，还可以读取和管理其所管理的企业卡的所有 `enterprise_card_bindings`。 |
| **商户用户 (Merchant User)** | 商家端的雇员，如收银员或店长。通过 Supabase Auth 认证并与特定商户绑定。 | `/(auth)/*`<br/>`/(merchant)/dashboard`<br/>`/(merchant)/charge`<br/>`/(merchant)/refund` | `merchant_charge_by_qr`<br/>`merchant_refund_tx` | 可以读取自己所属商户的 `merchants` 和 `merchant_users` 信息，以及所有与该商户相关的 `transactions`。 |
| **平台管理员 (Platform Admin)** | (这是一个隐含角色) 拥有系统最高管理权限，通常不通过前端标准流程操作，而是通过 Supabase Studio 或专用的后台系统进行管理。 | (不适用，通常通过 Supabase Studio 或专用后台) | (可调用所有 RPC) | 不受 RLS 限制 (使用 `service_role` key 时)。 |

### 权限实现要点

1.  **路由守卫 (Route Guarding)**:
    *   前端将通过检查用户的 `session` 来判断是否已登录。
    *   通过查询 `app.enterprise_card_bindings` 和 `app.merchant_users` 表（或创建一个 `get_my_roles` RPC）来确定用户的具体角色（如是否为企业管理员或商户用户）。
    *   基于角色来限制对 `/(enterprise)/*` 和 `/(merchant)/*` 路由组的访问。

2.  **RPC 调用**:
    *   所有写操作（支付、充值、绑定等）都封装在后端的 `SECURITY DEFINER` RPC 中。
    *   RPC 内部会进行严格的权限校验（例如，检查调用者是否为卡主、企业管理员或有效的商户用户）。
    *   即使前端UI出现漏洞，后端的 RPC 也能保证操作的安全性。

3.  **数据可见性 (RLS)**:
    *   数据库的行级安全策略 (RLS) 是数据隔离的最后一道防线。
    *   它确保即使用户通过 API 直接尝试读取数据，也只能获取到符合其身份和所有权策略的数据。