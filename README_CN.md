# MemberPaymentSystem (MPS) - README

## 概览

**MemberPaymentSystem (MPS)** 是一套基于 **Postgres + Supabase** 的会员、会员卡、支付系统解决方案。  
目标是提供一个安全、可扩展、支持企业卡和个人卡的支付与会员管理架构。

---

## ✨ 核心特性

1. **双卡模型**
   - **个人卡 (personal_card)**：自动根据积分调整等级与折扣。
   - **企业卡 (enterprise_card)**：固定折扣，可绑定多个用户，支持企业管理员。

2. **安全交易处理**
   - 所有支付/退款/充值 **必须通过 SECURITY DEFINER RPC** 完成。
   - 禁止直接写交易表，避免绕过业务逻辑。

3. **并发与幂等**
   - **行锁 + advisory 锁** 保证余额一致性。
   - **幂等键 (idempotency_key)** 防止重复入账。

4. **审计日志**
   - 每笔交易、充值、退款、绑定动作均记录 **操作者、时间、上下文**。

5. **动态二维码**
   - 仅存哈希值，15 分钟自动更新。
   - 商户收款时扫码校验。

6. **积分与等级**
   - 消费累计积分，触发自动升级/降级。
   - 折扣由等级表驱动，企业卡为固定折扣。

7. **分区存储**
   - 交易表 **按月分区**，便于归档与查询优化。

---

## 🗄️ 数据库结构

主要 Schema: `app` (业务) / `audit` (审计) / `sec` (安全工具)

### 表清单
- `app.member_profiles` - 会员资料
- `app.personal_cards` - 个人会员卡
- `app.enterprise_cards` - 企业会员卡
- `app.enterprise_card_bindings` - 企业卡与用户关系
- `app.transactions` - 交易记录（分区表）
- `app.point_ledger` - 积分流水
- `app.merchants` - 商户
- `app.merchant_users` - 商户操作员
- `audit.event_log` - 审计日志

### 枚举类型
- `card_type` = { personal, enterprise }
- `tx_type` = { payment, refund, recharge }
- `tx_status` = { processing, completed, failed, cancelled }
- `pay_method` = { balance, cash, wechat, alipay }
- `bind_role` = { admin, member }

---

## 🔒 权限与安全

- **默认 RLS 拒绝**，仅允许最小 `SELECT`。
- **禁止直接 INSERT/UPDATE/DELETE** 到资金表。  
- **所有写入必须走 RPC**：
  - `app.merchant_charge_by_qr(...)`
  - `app.merchant_refund_tx(...)`
  - `app.user_recharge_personal_card(...)`
  - `app.user_recharge_enterprise_card_admin(...)`
  - `app.enterprise_add_member(...)`
  - `app.enterprise_remove_member(...)`

---

## ⚡ RPC 列表与调用示例

### 1. 用户自助充值
```sql
select * from app.user_recharge_personal_card(
  '<personal_card_id>', 200.00, 'wechat', '自助充值', '{}'::jsonb, 'order-123', 'ide-123'
);
```

### 2. 商户扫码收款
```sql
select * from app.merchant_charge_by_qr(
  'SHOP-001',
  '<qr_code_plain>',
  52.00,
  '购买拿铁',
  '{"sku":"latte"}',
  'order-2025-0001'
);
```

### 3. 退款
```sql
select * from app.merchant_refund_tx(
  'SHOP-001',
  'ZF000123',
  20.00,
  '退货',
  '{}'::jsonb
);
```

### 4. 企业卡绑定
```sql
select app.enterprise_add_member('ENT00001','<member_id>','member');
select app.enterprise_remove_member('ENT00001','<member_id>');
```

---

## 🌐 前端接入

前端通过 `supabase-js` 调用 RPC：

```ts
const { data, error } = await supabase.rpc('merchant_charge_by_qr', {
  p_merchant_code: 'SHOP-001',
  p_qr_plain: qrValue,
  p_amount: 52.0,
  p_reason: '购买拿铁',
  p_tag: { sku: 'latte' },
  p_idempotency_key: 'order-2025-0001',
});
```

---

## 🚀 部署与运维

### 初始步骤
1. 在 Supabase SQL Editor 执行 `mps_full.sql`
2. 建立应用角色：
   ```sql
   create role app_role noinherit login password '***';
   ```
3. 授权：
   ```sql
   grant usage on schema app, audit, sec to app_role;
   grant select on app.v_user_cards, app.v_usage_logs to app_role;
   grant execute on function app.* to app_role;
   ```

### 定时任务
- 每月创建交易分区
- 定时更新过期卡片状态

### 监控
- 检查审计日志 `audit.event_log`
- 检查交易对账表

### 回滚策略
- 补偿表 `transaction_compensations`
- 幂等键防止重复入账

---

## 🔧 可扩展功能

- **多商户分润**：增加 `merchant_settlement` 表
- **优惠券系统**：增加 `coupons` 表及 RPC
- **营销活动**：增加 `campaigns` + 积分翻倍规则
- **财务对账**：支持外部支付网关回调

---

