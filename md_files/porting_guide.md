# Porting Guide（上线手册 + 前端对接指南）

> 目标：把 MPS 从开发环境平滑迁移到 Staging/Production，并指导前端稳定对接。

---

## 1. 环境与权限

- **数据库**：Supabase Postgres（开启 `pgcrypto`）。
- **Schema**：`app`/`audit`/`sec`；默认只读 `public`，务必切到 `app` 查看表。
- **账号**：
  - DBA：执行 DDL 与策略（SQL Editor Service Role）。
  - SRE：维护 Edge Functions 与 Cron 任务。
  - FE/BE：只需 `anon`/`service_role` key 调用 RPC。

---

## 2. 迁移步骤（建议分段执行，避免回滚）

### Step A. 初始化
- 执行：**schemas、extensions、enums、sequences、helpers**。  
- 校验：
  ```sql
  select schema_name from information_schema.schemata where schema_name in ('app','audit','sec');
  ```

### Step B. 建表 + 分区 + 注册表 + 审计
- 执行：`member_profiles ... enterprise_card_bindings ... transactions (parent) ... DO 块创建当月分区 ... tx/idempotency/merchant_order registries ... audit.event_log`。
- 校验：
  ```sql
  select schemaname, tablename from pg_tables where schemaname='app';
  select relname from pg_class where relname like 'transactions_%';
  ```

### Step C. 触发器 + RPC（SECURITY DEFINER）
- 执行：`after_insert_member_create_card()`、所有 RPC、修正版 `cron_expire_cards()`。
- 校验：
  ```sql
  select proname, prosecdef from pg_proc
  join pg_namespace n on n.oid=pg_proc.pronamespace
  where n.nspname='app' and prosecdef;  -- SECURITY DEFINER
  ```

### Step D. 视图
- 执行：`v_user_cards`、`v_usage_logs`。

### Step E. RLS 最后启用
- 执行：`enable row level security` + `deny_all` + `*read` 策略。
- 校验：通过 `auth.uid()` 的会话读取数据，写操作只能走 RPC。

---

## 3. 数据初始化与验收用例

- 等级配置：内置 Lv0~Lv4；可在 `membership_levels` 调整。
- 商户：创建 `merchants(code)`，并把收银员加入 `merchant_users`。
- 最少用例：
  1. 插入 `member_profiles(id=auth.uid())` → 自动发个人卡。
  2. 旋转个人卡二维码 → 商户扫码支付 → 退款 → 充值。

---

## 4. 运行维护

- **分区管理**：每月初执行 DO 块创建当月分区和索引；或实现 `ensure_next_month_partition()` 并由 Edge Function 定时调用。
- **过期处理**：`cron_expire_cards()`（修正版）。
- **备份与恢复**：按月分区做逻辑备份；优先备份 registries 与最新月交易分区。
- **监控**：
  - 错误审计（`audit.event_log`）。
  - 幂等冲突（`idempotency_registry`）。
  - 分区缺失（`select relname from pg_class where relname like 'transactions_%'`）。

---

## 5. 前端对接（页面与 RPC 映射）

| 页面/模块 | RPC | 备注 |
|---|---|---|
| 我的卡片 | `v_user_cards`（只读） | 展示余额/等级/折扣 |
| 展示二维码 | `rotate_card_qr` | 返回明文二维码 + 15 分钟过期时间 |
| 扫码收款（商户） | `merchant_charge_by_qr` | 需登录为商户成员 |
| 退款（商户） | `merchant_refund_tx` | 仅对“完成的支付”可退，支持部分多次 |
| 个人充值 | `user_recharge_personal_card` | 支付完成回调后调用 |
| 企业充值 | `user_recharge_enterprise_card_admin` | 仅企业管理员 |
| 企业绑定 | `enterprise_add_member` / `enterprise_remove_member` / `enterprise_set_initial_admin` | 绑定需卡密码 |

---

## 6. 回滚与应急

- 回滚 DDL：保持一套“上一个稳定版本” SQL，使用 `BEGIN; ...; COMMIT;` 批量回退。
- 交易补偿：
  - 如果第三方支付已扣款但交易未写表：根据外部订单号在 `merchant_order_registry` 查询并重放。
  - 如余额异常：以 RPC 的“人工调整余额”功能（可扩展）在审计下进行纠偏。

---

## 7. 常见问题（FAQ）

- **执行完没有表？**  
  可能最后一条语句报错导致整批回滚；请分段执行，或查看 SQL History 的错误信息。并切换 Table Editor 的 schema 为 `app`。

- **`permission denied for table`？**  
  写操作只能走 RPC；读表需满足 RLS 条件。

- **`unrecognized GET DIAGNOSTICS item`？**  
  使用 `GET DIAGNOSTICS v_row = ROW_COUNT; v_cnt := v_cnt + v_row;` 的修正版。
