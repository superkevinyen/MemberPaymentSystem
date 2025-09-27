# Member Payment System (MPS) — README

> 方案：**A（商用推荐）**：交易按月分区 + 分区内唯一索引 + 全局注册表（`tx_registry` / `idempotency_registry` / `merchant_order_registry`）+ 仅通过 **SECURITY DEFINER RPC** 写入资金类表。

---

## 1. 项目目标与功能清单

- **会员体系**
  - 个人卡：与会员 1:1 绑定；积分 → 等级 → 动态折扣。
  - 企业卡：一个企业卡可绑定多人；**固定折扣**；仅企业管理员可管理成员与充值。
  - 动态二维码：15 分钟有效；仅存 **bcrypt 哈希**，扫描时进行校验。
- **交易能力**
  - 支付 / 退款 / 充值（个人、企业）全流程。
  - **并发安全**：行级锁 + advisory 锁（按卡维度）。
  - **幂等**：`idempotency_registry` 全局表；重复请求返回同一结果。
  - **外部订单去重**：`merchant_order_registry` 按（merchant_id, external_order_id）唯一。
- **安全与合规**
  - **RLS 默认拒绝**，仅最小读取策略；**所有写入只允许走 RPC**。
  - 统一审计：`audit.event_log` 记录每次资金操作。
- **可运维**
  - 交易表按月分区，便于归档与检索。
  - 提供过期卡失效定时任务函数 `cron_expire_cards()`。

---

## 2. 架构与对象分布

- `app`：业务核心（会员、卡、绑定、商户、交易分区、积分流水、全局注册表、RPC）。
- `audit`：审计日志（`event_log` + `audit.log()`）。
- `sec`：安全工具（固定 `search_path`、哈希锁 key 计算）。

核心表（`app.*`）：

| 表名 | 作用 | 关键字段 |
|---|---|---|
| `member_profiles` | 会员资料（外键指向 `auth.users(id)`） | `member_no`、`status` |
| `personal_cards` | 个人卡（1:1） | `balance`、`points`、`level`、`discount`、`qr_code_hash/updated_at` |
| `enterprise_cards` | 企业卡 | `company_name`、`fixed_discount`、`password_hash`、`balance` |
| `enterprise_card_bindings` | 企业卡-会员绑定关系 | `role`（`admin/member`）唯一键 `(enterprise_card_id, member_id)` |
| `merchants` / `merchant_users` | 商户及其成员 | `code` 唯一 |
| `membership_levels` | 等级-折扣区间配置 | `min_points/max_points/discount` 不重叠校验 |
| `transactions` | 交易（**父表**，按 `created_at` RANGE 分区） | 见下 |
| `point_ledger` | 积分流水（仅个人卡） | `delta`、`balance_after` |
| `tx_registry` | 交易号全局唯一 | `tx_no -> tx_id` |
| `idempotency_registry` | 幂等键全局唯一 | `idempotency_key -> tx_id` |
| `merchant_order_registry` | 商户外部订单唯一 | `unique(merchant_id, external_order_id)` |

**交易分区**：父表 `app.transactions` 以 `created_at` 做 RANGE 分区；每月一个分区，例如 `transactions_y2025m09`。在每个分区上创建：

- `unique(id)`、`unique(tx_no)`、`unique(idempotency_key) where not null`、`unique(merchant_id, external_order_id) where not null`
- 常用查询索引：`(card_id, created_at desc)`、`(merchant_id, created_at desc)`、`(status)`

---

## 3. 安全模型（RLS + RPC）

- **默认拒绝**：所有核心表先创建 `deny_all` 策略（`using false with check false`）。
- **最小读取**：仅对“当前登录用户自身数据”开放只读策略；示例：
  - 用户只能读取自己 `member_profiles` 与 `personal_cards`；
  - 仅绑定成员可读企业卡；仅企业管理员可管理成员；
  - 交易查询对三类主体开放：个人卡持有人、企业卡绑定成员、该商户的成员。
- **写入**：资金相关表（交易、余额、积分、绑定）**不提供任何 INSERT/UPDATE/DELETE 策略**；写入只能通过 **SECURITY DEFINER** 的 RPC 完成，RPC 内部进行鉴权与加锁。

---

## 4. RPC 目录与签名

> 全部函数均在 `app` schema，且默认 `SECURITY DEFINER`。

### 4.1 二维码
- `rotate_card_qr(p_card_id uuid, p_card_type app.card_type) returns table(qr_plain text, qr_expires_at timestamptz)`  
  - 个人卡：仅卡主可旋转；企业卡：仅管理员可旋转。返回明文二维码（只用于前端展示），同时在表内保存 **bcrypt 哈希** 与更新时间。

### 4.2 企业卡绑定
- `enterprise_set_initial_admin(p_card_no text, p_member_no text) returns boolean`  
  - 设置某会员为该企业卡的初始管理员。
- `enterprise_add_member(p_card_no text, p_member_no text, p_card_password text) returns boolean`  
  - 企业管理员 + 正确卡密码 才能绑定成员。
- `enterprise_remove_member(p_card_no text, p_member_no text) returns boolean`  
  - 管理员可解绑任意成员；成员可自解绑。

### 4.3 交易
- `merchant_charge_by_qr(p_merchant_code text, p_qr_plain text, p_raw_price numeric, p_reason text default null, p_tag jsonb default '{}'::jsonb, p_idempotency_key text default null, p_external_order_id text default null)`  
  **returns** `(tx_id uuid, tx_no text, card_type app.card_type, card_id uuid, final_amount numeric, discount numeric)`  
  - 商户扫码收款；支持幂等与外部订单去重；个人卡会计算积分与折扣并升级等级；企业卡采用固定折扣。

- `merchant_refund_tx(p_merchant_code text, p_original_tx_no text, p_refund_amount numeric, p_reason text default null, p_tag jsonb default '{}'::jsonb)`  
  **returns** `(refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)`  
  - 仅对 **完成的支付** 支持部分/多次退款；自动回充余额。

### 4.4 充值
- `user_recharge_personal_card(p_personal_card_id uuid, p_amount numeric, p_payment_method app.pay_method default 'wechat', p_reason text default null, p_tag jsonb default '{}'::jsonb, p_idempotency_key text default null, p_external_order_id text default null)`  
  **returns** `(tx_id uuid, tx_no text, card_id uuid, amount numeric)`

- `user_recharge_enterprise_card_admin(p_enterprise_card_id uuid, p_amount numeric, p_payment_method app.pay_method default 'wechat', p_reason text default null, p_tag jsonb default '{}'::jsonb, p_idempotency_key text default null, p_external_order_id text default null)`  
  **returns** `(tx_id uuid, tx_no text, card_id uuid, amount numeric)`  
  - 仅企业管理员可调用。

### 4.5 维护
- `cron_expire_cards() returns int`：失效已过期的个人卡与企业卡，并写审计。

---

## 5. 典型流程（端到端）

### 5.1 新用户注册 → 自动发卡
1. 用户通过 Supabase Auth 注册。
2. 业务侧插入 `app.member_profiles(id=auth.users.id, ...)`。
3. 触发器 `after_insert_member_create_card()` 自动为其创建一张个人卡（`level=0, discount=1.000`）。

### 5.2 用户展示二维码给商户收款
1. 用户调用 `rotate_card_qr(card_id,'personal')` 获取 **明文**二维码与过期时间。
2. 商户前端扫码后调用 `merchant_charge_by_qr('M001', qr_plain, 25.5, 'coffee', '{"sku":"latte"}')`。
3. RPC 内部：鉴权商户 → 匹配 QR（15 分钟 + bcrypt 校验）→ 加锁 → 计算折扣与积分 → 写交易分区表 → 更新余额与积分 → 完成交易。

### 5.3 退款
1. 商户在订单详情页选择退款金额。
2. 调用 `merchant_refund_tx('M001', original_tx_no, 10.00, 'customer_request')`。
3. RPC 内部：检查剩余可退金额 → 加锁卡片 → 新建一条 `refund` 交易 → 回充余额。

### 5.4 充值
- 个人卡：`user_recharge_personal_card(card_id, amount, 'wechat', 'topup')`
- 企业卡：`user_recharge_enterprise_card_admin(card_id, amount, 'alipay', 'corporate_topup')`（需管理员）

---

## 6. 安装与验证（Supabase）

> 推荐**分段执行** `mps_full.sql`，避免整批回滚。

1) **Schemas & 扩展 & 枚举 & 序列 & helpers**  
2) **表（不含 RLS） + 分区（DO 块创建当月分区） + 注册表 + 审计表**  
3) **触发器 & 全量 RPC（注意使用修正版 `cron_expire_cards()`）**  
4) **视图**  
5) **最后启用 RLS & 策略**  

验证命令：

```sql
-- 看到三个 schema（app/audit/sec）
select schema_name from information_schema.schemata where schema_name in ('app','audit','sec');

-- 看到 app 下的表
select schemaname, tablename from pg_tables where schemaname='app' order by tablename;

-- 看到当月交易分区
select relnamespace::regnamespace as schema, relname from pg_class where relname like 'transactions_%' order by relname;
```

最少数据流测试：

```sql
-- 建商户 & 绑定自己为 cashier
insert into app.merchants(name, code) values ('Test Merchant','M001')
on conflict (code) do update set name=excluded.name;

insert into app.merchant_users(merchant_id, user_id, role)
select id, auth.uid(), 'cashier' from app.merchants where code='M001'
on conflict do nothing;

-- 插入会员资料（与当前会话 auth.uid() 绑定）
insert into app.member_profiles(id, name) values (auth.uid(), 'Demo User')
on conflict (id) do nothing;

-- 查个人卡
select * from app.personal_cards where member_id=auth.uid();

-- 旋转二维码
select * from app.rotate_card_qr('<personal_card_id>','personal');

-- 商户收款
select * from app.merchant_charge_by_qr('M001','<qr_plain>', 25.50,'coffee','{"sku":"latte"}');
```

---

## 7. 前端接入示例

### 7.1 JavaScript（Supabase-js）
```js
import { createClient } from "@supabase/supabase-js";
const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

// 旋转二维码（个人卡）
const { data: qr } = await supabase.rpc("rotate_card_qr", { p_card_id: cardId, p_card_type: "personal" });
// qr: [{ qr_plain, qr_expires_at }]

// 商户收款（扫码后）
const { data: pay, error } = await supabase.rpc("merchant_charge_by_qr", {
  p_merchant_code: "M001",
  p_qr_plain: scannedQR,
  p_raw_price: 25.50,
  p_reason: "coffee",
  p_tag: { sku: "latte" },
  p_idempotency_key: crypto.randomUUID()
});
```

### 7.2 Python
```python
from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 退款
res = supabase.rpc("merchant_refund_tx", {
  "p_merchant_code": "M001",
  "p_original_tx_no": "ZF000123",
  "p_refund_amount": 10.00,
  "p_reason": "customer_request"
}).execute()
```

---

## 8. 维护与运维

- **创建下月分区**：同样使用 DO 块（或在 Edge Function 定时调用一个 `ensure_next_month_partition()` 函数）。
- **清理**：归档旧分区，或把旧月分区移动到冷存储库。
- **监控**：
  - 错误审计：`select * from audit.event_log order by happened_at desc limit 100;`
  - 幂等冲突：查询 `idempotency_registry` 与 `merchant_order_registry`。
  - 分区缺失：`select relname from pg_class where relname like 'transactions_%';`
- **常见问题**：
  - 只看到 `public`：到 Table Editor 左上角切换 schema 为 `app`。
  - 执行到最后报错 → **整批回滚**：分段执行。
  - `permission denied`：写操作需要走 RPC；确认 RLS 策略。

---

## 9. 变更与扩展（Roadmap）

- 优惠券/促销、商户结算周期、导出对账单、风控黑名单、多币种、多语言。
- GraphQL 只读查询（结合 RLS），写操作仍走 RPC。
- 引入任务队列（如 Resend/第三方支付回调处理），实现最终一致。

---

## 10. 版本记录（关键节点）

- v1.0（当前）：按月分区 + 全局注册表 + 全量 RPC + 审计 + RLS 最小读取。
- 下一步：自动生成下月分区函数；对账视图；对异常交易补偿表。
