# plan_guide.md

## 🎯 项目目标
构建一套 **会员支付系统 (MemberPaymentSystem, MPS)**，支持：
- **个人会员卡**：积分驱动等级与折扣，自动升级。
- **企业会员卡**：固定折扣，多用户绑定，管理员控制。
- **支付 / 退款 / 充值**：全部走 **安全 RPC**，保证幂等、并发安全、审计记录。
- **多端接入**：网页端先行，未来扩展至小程序 / App / 合作方 API。

---

## 🏗️ 架构设计

### 数据层（Postgres + Supabase）
- **核心表**：`member_profiles`, `personal_cards`, `enterprise_cards`, `enterprise_card_bindings`, `transactions`, `point_ledger`, `merchants`, `merchant_users`
- **安全机制**：
  - RLS：所有资金表禁止直接写入。
  - SECURITY DEFINER RPC：写操作必须走函数。
  - 审计日志 `audit.event_log`：记录所有敏感操作。

### 功能模块
1. **用户与会员卡**
   - 新用户自动生成个人卡。
   - 企业管理员可绑定/解绑成员。
   - 用户可自助解绑企业卡。
2. **交易与支付**
   - 二维码 15 分钟有效，只存哈希。
   - 商户扫码完成支付。
   - 积分自动累计，个人卡自动调整等级与折扣。
3. **退款 / 充值**
   - 退款：原路退回，支持部分退款。
   - 充值：个人自助充值，企业需管理员操作。
4. **并发与幂等**
   - 行锁 + advisory 锁防止并发错误。
   - 幂等键 `idempotency_key` 避免重复入账。
5. **分区与定时任务**
   - 交易表按月分区。
   - 定时任务（Edge Function）：创建下月分区、扫描过期二维码。

---

## 🔑 权限模型

| 身份 | 权限 |
|------|------|
| 普通会员 | 使用个人卡，查看并充值自己的卡，自助解绑企业卡 |
| 企业成员 | 使用企业卡消费，但不能绑定/充值 |
| 企业管理员 | 企业卡充值、绑定/解绑用户、刷新企业卡二维码 |
| 商户操作员 | 收款、退款 |
| 系统管理员 | 全权限（运维） |

---

## 🖥️ 实施步骤

### 阶段 0（当前）
- ✅ 数据库脚本（mps_full.sql）已完成设计
- ✅ RLS 策略与安全 RPC 已定义
- ✅ README 与 Porting Guide 已生成

### 阶段 1（近期目标）
- [ ] 用 Next.js + Supabase 构建前端原型  
  - 登录（Supabase Auth）  
  - 我的卡片 / 积分等级  
  - 付款码生成（调用 `rotate_card_qr`）  
  - 消费 / 充值 / 退款操作（调用 RPC）  
  - 交易明细页面（`v_usage_logs`）  
- [ ] 商户端界面：扫码支付 + 退款  

### 阶段 2（中期）
- [ ] Edge Functions：  
  - 定时任务（过期二维码、月度分区）  
  - 第三方支付回调（微信/支付宝）  
- [ ] API 封装（REST/GraphQL）：对外提供统一接口  
- [ ] 错误码映射与文档化  

### 阶段 3（长期）
- [ ] SDK 封装（JS/TS/Python 等）  
- [ ] 小程序前端接入（调用 API）  
- [ ] 报表/对账模块  
- [ ] 优惠券/营销活动模块  

---

## 📊 当前进度追踪

- [x] 数据库架构设计完成  
- [x] mps_hardened.sql + mps_addons.sql 合并 → mps_full.sql  
- [x] README.md 与 porting_guide.md 初版 & 完整版  
- [ ] plan_guide.md （本文件 ✅）  
- [ ] 前端原型（待开发）  
- [ ] Edge Functions 定时任务（待开发）  
- [ ] 对外 API （待开发）  

---

👉 建议现在的重点：  
1. 直接用 **Next.js + Supabase-js** 跑通完整流程（会员卡 → 二维码 → 商户收款 → 交易明细）。  
2. 跑通后，再补 Edge Function（分区 + 定时任务）。  
3. 之后再考虑 API 封装 / 小程序接入。  
