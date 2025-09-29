
# Member Payment System (MPS) — 業務流程梳理

本文描述了 MPS 的核心業務流程 (Use Cases)，涵蓋會員、商戶、平台管理員三大角色，並窮舉主要業務場景與限制。

---

## 🔑 卡片綁定規則總覽

| 卡片類型 | 說明 | 是否可共享 | 綁定需求 | 密碼需求 | 特殊限制 |
|----------|------|------------|-----------|-----------|-----------|
| **標準卡 (standard)** | 每個會員必備的身份卡，註冊自動生成 | ❌ 單人專屬 | 自動與會員綁定 (owner) | 無 (密碼為 NULL) | 只能 1 對 1，不能共享 |
| **預付卡 (prepaid)** | 可充值、多人共享的儲值卡 | ✅ 可共享 | 手動綁定 | 需要輸入綁定密碼 | 至少一個 owner |
| **企業卡 (corporate)** | 企業或組織發行，可多人使用 | ✅ 可共享 | 由 owner 邀請或密碼綁定 | 需密碼或授權 | 至少一個 owner |
| **優惠券卡 (voucher)** | 折扣/一次性優惠用途 | ❌ 不可共享 | 單一會員綁定 | 無 | 到期自動失效 |

---

## 1. 登入與身份綁定

### 1.1 平台管理員登入
- **入口**: Supabase Auth (`auth.users`)
- **用途**: 管理員登入控制台，進行商戶/會員管理
- **權限**: `platform_admin` 角色

### 1.2 會員登入 (App / 小程序)
- **入口**: 外部身份 (WeChat, Alipay, Line…)
- **流程**:
  1. 用戶於小程序授權 → 獲取外部 `openid`
  2. 調用 `bind_external_identity(member_id, provider, external_id)`
  3. 若無對應會員 → `create_member_profile(...)` → 自動生成標準卡
- **表**: `member_profiles`, `member_external_identities`, `member_cards`

---

## 2. 會員管理

### 2.1 新增會員
- **入口**: 管理員或自助註冊
- **RPC**: `create_member_profile`
- **副作用**: 自動生成 `standard` 卡，並綁定為 `owner`
- **表**: `member_profiles`, `member_cards`, `card_bindings`
- **限制**:
  - 每個會員必須有一張標準卡
  - 標準卡 `binding_password_hash = NULL`

### 2.2 綁定外部身份
- **RPC**: `bind_external_identity`
- **場景**: 綁定 WeChat openid / Alipay uid / Line id
- **唯一性**: 一個 provider 的 external_id 只能綁一個會員
- **錯誤碼**: `EXTERNAL_ID_ALREADY_BOUND`

### 2.3 綁定共享卡
- **RPC**: `bind_member_to_card`
- **卡片邏輯**:
  - **standard**: 不允許綁定其他會員 (只能 1 對 1)
  - **prepaid**: 支援共享，需驗證密碼
  - **corporate**: 支援共享，需驗證密碼或由 owner 授權
  - **voucher**: 不允許共享
- **錯誤碼**:
  - `INVALID_BINDING_PASSWORD`
  - `CARD_NOT_FOUND_OR_INACTIVE`
  - `ROLE_CONFLICT`

### 2.4 解绑共享卡
- **RPC**: `unbind_member_from_card`
- **限制**: 不能移除最後一個 owner
- **錯誤碼**: `CANNOT_REMOVE_LAST_OWNER`

---

## 3. 卡片與 QR Code

### 3.1 QR Code 生成
- **標準卡**: 即時生成 → `rotate_card_qr(card_id, ttl)`
- **預付/企業卡**: 週期自動生成 → `cron_rotate_qr_tokens(ttl)`
- **表**: `card_qr_state`, `card_qr_history`

### 3.2 QR Code 掃碼驗證
- **RPC**: `validate_qr_plain(qr_plain)`
- **錯誤碼**:
  - `INVALID_QR`
  - `QR_EXPIRED_OR_INVALID`

---

## 4. 交易流程

### 4.1 支付
**流程**:
1. 商戶 POS 掃描會員 QR → 得到 `qr_plain`
2. 調用 `merchant_charge_by_qr`
   - 驗證商戶合法性 (`merchant_users`)
   - `validate_qr_plain` → 得到 `card_id`
   - `pg_advisory_xact_lock(card_id)` → 鎖定卡片
   - 檢查餘額 → 計算折扣
   - 插入 `transactions (payment)`
   - 更新 `member_cards.balance`、積分、等級
   - 寫入 `audit.event_log`
3. 返回 `tx_no, final_amount, discount`

**錯誤碼**:
- `INSUFFICIENT_BALANCE`
- `QR_EXPIRED_OR_INVALID`
- `NOT_MERCHANT_USER`
- `UNSUPPORTED_CARD_TYPE_FOR_PAYMENT`

### 4.2 退款
**流程**:
1. 商戶輸入原交易號 `tx_no`
2. 調用 `merchant_refund_tx`
   - 驗證原交易屬於該商戶
   - 驗證狀態為 `completed`
   - 計算可退金額 (partial / multiple allowed)
   - 鎖定卡片 → 插入退款交易
   - 更新餘額
   - 寫入 `audit.event_log`
3. 返回 `refund_tx_no, refunded_amount`

**錯誤碼**:
- `ONLY_COMPLETED_PAYMENT_REFUNDABLE`
- `REFUND_EXCEEDS_REMAINING`

### 4.3 充值
**流程**:
1. 會員於 App 選擇卡片與金額
2. 調用第三方支付 → `external_order_id`
3. 調用 `user_recharge_card`
   - `pg_advisory_xact_lock(card_id)`
   - 插入 `transactions (recharge)`
   - 更新 `member_cards.balance`
   - 寫入 `audit.event_log`
4. 返回 `tx_no, amount`

**錯誤碼**:
- `INVALID_RECHARGE_AMOUNT`
- `CARD_NOT_FOUND_OR_INACTIVE`

---

## 5. 積分與等級

### 5.1 積分累積
- **場景**: 消費支付成功後 → 系統自動增加積分
- **RPC**: 內部在 `merchant_charge_by_qr` 寫入 `point_ledger`
- **表**: `point_ledger`

### 5.2 等級升降
- **RPC**: `update_points_and_level`
- **表**: `membership_levels`, `member_cards`

---

## 6. 結算

### 6.1 商戶結算
- **模式**: `realtime | t_plus_1 | monthly`
- **RPC**: `generate_settlement`
- **表**: `settlements`

### 6.2 對帳報表
- **RPC**: `list_settlements`, `get_merchant_transactions`
- **用途**: 商戶對帳 / 平台財務核對

---

## 7. 風控與管理

### 7.1 凍結/解凍卡片
- **RPC**: `freeze_card`, `unfreeze_card`
- **場景**: 卡片掛失、風控暫停使用

### 7.2 封禁會員/商戶
- **RPC**: `admin_suspend_member`, `admin_suspend_merchant`
- **場景**: 違規會員、商戶

---

## 8. 常見 Use Cases 總覽

| 流程 | 角色 | 主要 RPC | 關聯表 |
|------|------|----------|--------|
| 登入 (微信) | 會員 | bind_external_identity | member_external_identities |
| 新增會員 | 管理員/會員 | create_member_profile | member_profiles, member_cards |
| 綁定共享卡 | 會員 | bind_member_to_card | card_bindings |
| 支付 | 商戶 | merchant_charge_by_qr | transactions, point_ledger |
| 退款 | 商戶 | merchant_refund_tx | transactions |
| 充值 | 會員 | user_recharge_card | transactions |
| 積分升級 | 系統 | update_points_and_level | membership_levels |
| 商戶結算 | 管理員 | generate_settlement | settlements |
| 凍結卡片 | 管理員 | freeze_card | member_cards |

---

## 9. 業務場景流程 (窮舉)

### 9.1 註冊會員流程
1. 用戶於 App 授權登入
2. 系統查詢外部綁定 → 無則新增會員
3. 調用 `create_member_profile` → 自動生成標準卡
4. 插入 `card_bindings (owner, 無密碼)`

**限制**:
- 每個會員必須有一張標準卡
- 標準卡不可共享

---

### 9.2 綁定共享卡流程
1. 會員輸入卡號或掃碼
2. 系統檢查卡片狀態是否 active
3. 若為 `prepaid/corporate` → 驗證密碼
4. 調用 `bind_member_to_card`
5. 寫入 `audit.event_log`

**限制**:
- standard/voucher 不可共享
- 預付/企業卡需密碼
- 不可移除最後 owner

---

### 9.3 支付流程
1. 商戶掃描 QR
2. 調用 `merchant_charge_by_qr`
3. 驗證商戶與卡片 → 計算折扣
4. 插入交易、更新餘額與積分
5. 返回 `tx_no` 與金額

**限制**:
- 餘額不足 → `INSUFFICIENT_BALANCE`
- QR 過期 → `QR_EXPIRED_OR_INVALID`

---

### 9.4 退款流程
1. 商戶輸入原交易號
2. 調用 `merchant_refund_tx`
3. 驗證交易狀態 → 插入退款交易
4. 更新餘額 → 返回退款流水號

**限制**:
- 只能退已完成交易
- 多次部分退款需小於可退金額

---

### 9.5 充值流程
1. 用戶於 App 發起充值
2. 調用第三方支付 → 返回訂單號
3. 調用 `user_recharge_card`
4. 插入充值交易 → 更新餘額

**限制**:
- 金額必須 > 0
- 卡片必須為 active

---

### 9.6 積分升級流程
1. 消費成功 → 增加積分
2. 調用 `update_points_and_level`
3. 達門檻 → 自動升級折扣

---

### 9.7 商戶結算流程
1. 系統定期呼叫 `generate_settlement`
2. 聚合商戶交易與退款
3. 插入 `settlements` → 返回報表

**限制**:
- 無交易則報錯 `NO_TRANSACTIONS_IN_PERIOD`

---

### 9.8 風控流程
- **凍結卡片**: `freeze_card` → 更新狀態 → 拒絕後續支付  
- **封禁會員**: `admin_suspend_member` → 更新狀態 → 拒絕充值/支付  

---

*End of business flows*
