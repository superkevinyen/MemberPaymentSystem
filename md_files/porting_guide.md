# MemberPaymentSystem - Porting Guide

## 🎯 目标

本手册指导如何将 `mps_full.sql` 从开发环境迁移到生产环境，并确保系统安全、稳定。

---

## 📦 部署步骤

### 1. 执行数据库脚本
在 Supabase SQL Editor 中运行：
```sql
\i mps_full.sql
```

### 2. 创建应用角色
```sql
create role app_role noinherit login password '***';
```

### 3. 授权
```sql
grant usage on schema app, audit, sec to app_role;
grant select on app.v_user_cards, app.v_usage_logs to app_role;
grant execute on function
  app.rotate_card_qr,
  app.merchant_charge_by_qr,
  app.merchant_refund_tx,
  app.user_recharge_personal_card,
  app.user_recharge_enterprise_card_admin,
  app.enterprise_add_member,
  app.enterprise_remove_member
to app_role;
```

### 4. 初始化商户
```sql
insert into app.merchants(name, code) values ('Demo Shop', 'SHOP-001');
insert into app.merchant_users(merchant_id, user_id, role)
select id, '<auth-user-id>', 'cashier' from app.merchants where code='SHOP-001';
```

### 5. 初始化会员
- 用户通过 Supabase Auth 注册 → 自动生成 `member_profiles`
- 触发器会同步生成一张个人卡

---

## 🛠️ 运维要点

### 定时任务
- 每月执行：`app.create_next_partition()`
- 每日执行：`app.expire_qrcodes()`

### 审计与监控
- 所有敏感操作写入 `audit.event_log`
- 定期审查 `failed` 或 `cancelled` 状态交易

### 回滚机制
- 使用 `transaction_compensations` 表记录并追踪补偿

### 错误码
- RPC 返回统一结构： `{ code, message, tx_id }`
- 前端需根据 `code` 做提示或重试

---

## 📲 前端对接指南

- 使用 **supabase-js** 调用 `rpc()`
- 核心页面：
  - 我的卡片
  - 扫码支付
  - 充值
  - 退款申请
  - 积分流水

示例：
```ts
const { data, error } = await supabase.rpc('user_recharge_personal_card', {
  p_card_id: cardId,
  p_amount: 200,
  p_method: 'wechat',
  p_reason: '充值',
  p_metadata: {},
  p_ext_order_id: 'order-123',
  p_idempotency_key: 'ide-123'
});
```

---

## 🔐 安全与隐私

- 不存储明文二维码，只存哈希
- 企业卡绑定必须由企业管理员操作
- 所有写操作仅能通过 RPC 完成

---

