
# Member Payment System (MPS) — 業務流程梳理

本文描述了 MPS 的核心業務流程 (Use Cases)，涵蓋會員、商戶、平台管理員三大角色，並窮舉主要業務場景與限制。

---

## 🔑 卡片綁定規則總覽

> 💡 **2025-10-01 更新**: 系統已簡化為 3 種卡片類型，移除 Prepaid Card。詳見 [重構文檔](plans/REFACTOR_CARD_SYSTEM.md)

| 卡片類型 | 說明 | 是否可共享 | 綁定需求 | 密碼需求 | 特殊限制 |
|----------|------|------------|-----------|-----------|-----------|
| **標準卡 (standard)** | 統一會員卡，支持充值、消費、積分 | ❌ 單人專屬 | 自動與會員綁定 (owner) | 無 | 只能 1 對 1，不能共享 |
| **企業卡 (corporate)** | 企業折扣卡，提供固定折扣給員工 | ✅ 可共享 | 由 owner 邀請或密碼綁定 | 需密碼或授權 | 不可充值、不可消費，只提供折扣 |
| **優惠券卡 (voucher)** | 折扣/一次性優惠用途 | ❌ 不可共享 | 單一會員綁定 | 無 | 到期自動失效 |

### 🆕 企業折扣邏輯

當會員綁定企業卡後：
- 會員的 Standard Card 會記錄 `corporate_discount`（企業折扣）
- 支付時自動選擇最優折扣：`LEAST(積分等級折扣, 企業折扣)`
- 解綁後，`corporate_discount` 清除，恢復使用積分等級折扣

**示例**：
```
會員積分折扣：0.90（金卡）
企業折扣：0.85
實際使用：0.85（更優惠）

解綁後：
實際使用：0.90（恢復積分折扣）
```

---

## 1. 登入與身份認證

### 1.1 超級管理員登入 (Super Admin)
- **登入方式**: Supabase Auth (`auth.users`)
- **角色**: `super_admin` (唯一管理員角色)
- **關聯表**: `admin_users` (通過 `auth_user_id` 關聯)
- **權限**: 全部系統功能，繞過所有 RLS 限制
- **用途**: 系統管理、會員/商戶管理、數據維護

### 1.2 會員登入 (Member)

**三種登入方式**：

#### A. 自定義密碼登入 (推薦用於 CLI/POS)
- **RPC**: `member_login(p_identifier, p_password)`
- **識別符**: 手機號碼或會員號 (member_no)
- **返回**: `session_id`, `expires_at` (24小時有效)
- **流程**:
  1. 輸入手機/會員號 + 密碼
  2. 系統驗證 `member_profiles.password_hash`
  3. 生成 session 存入 `app_sessions` 表
  4. 返回 session_id 用於後續 RPC 調用

#### B. Supabase Auth 登入 (用於 Web/App)
- **登入**: 使用 Supabase Auth (Email/Password, OAuth)
- **關聯**: `member_profiles.auth_user_id` 關聯 `auth.users(id)`
- **識別**: 通過 `auth.uid()` 自動識別
- **用途**: Web 應用、移動 App

#### C. 外部身份綁定 (用於小程序)
- **平台**: 微信、支付寶、Line 等
- **綁定表**: `member_external_identities`
- **流程**:
  1. 用戶於小程序授權 → 獲取 `openid`
  2. 查詢 `member_external_identities` 找到對應會員
  3. 若無對應會員 → 調用 `create_member_profile` 創建
- **表**: `member_profiles`, `member_external_identities`

### 1.3 商戶登入 (Merchant)

**兩種登入方式**：

#### A. 自定義密碼登入 (推薦用於 POS)
- **RPC**: `merchant_login(p_merchant_code, p_password)`
- **識別符**: 商戶代碼 (merchant_code)
- **返回**: `session_id`, `expires_at`
- **流程**:
  1. 輸入商戶代碼 + 密碼
  2. 系統驗證 `merchants.password_hash`
  3. 生成 session 存入 `app_sessions`
  4. 返回 session_id

#### B. Supabase Auth 登入 (用於 Web)
- **登入**: 使用 Supabase Auth
- **關聯**: `merchant_users` 表關聯 `auth.users` 和 `merchants`
- **用途**: 商戶管理後台

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

### 2.3 綁定企業折扣卡
- **RPC**: `bind_member_to_card(p_card_id, p_member_id, p_role, p_binding_password, p_session_id)`
- **卡片邏輯**:
  - **standard**: 不允許綁定其他會員 (只能 1 對 1)
  - **corporate**: 支援共享，需驗證密碼或由 owner 授權
    - 綁定後會設置會員 Standard Card 的 `corporate_discount`
    - 支付時自動選擇最優折扣：`LEAST(積分折扣, 企業折扣)`
  - **voucher**: 不允許共享
- **角色類型**: `owner` | `admin` | `member` | `viewer`
- **錯誤碼**:
  - `INVALID_BINDING_PASSWORD` - 綁定密碼錯誤
  - `CARD_NOT_FOUND_OR_INACTIVE` - 卡片不存在或未激活
  - `CARD_TYPE_NOT_SHAREABLE` - 卡片類型不支持共享
  - `CARD_OWNER_NOT_DEFINED` - 企業卡未設置 owner

### 2.4 解綁共享卡
- **RPC**: `unbind_member_from_card(p_card_id, p_member_id, p_session_id)`
- **副作用**: 若解綁企業卡，會清除會員 Standard Card 的 `corporate_discount`
- **限制**: 不能移除最後一個 owner
- **錯誤碼**: `CANNOT_REMOVE_LAST_OWNER`

---

## 3. 卡片與 QR Code

### 3.1 QR Code 生成
- **RPC**: `rotate_card_qr(p_card_id, p_ttl_seconds, p_session_id)`
- **權限控制**:
  - ✅ **Super Admin**: 可為任何卡片生成 QR（測試和管理用途）
  - ✅ **Member**: 只能為自己擁有或綁定的卡片生成 QR
  - ❌ **Merchant**: 不能生成 QR 碼（只能掃碼收款）
- **卡片類型**:
  - **Standard Card**: 可生成 QR，用於支付
  - **Corporate Card**: 不可生成 QR（只提供折扣，不能直接支付）
  - **Voucher Card**: 可生成 QR，用於一次性消費
- **表**: `card_qr_state`, `card_qr_history`
- **預設 TTL**: 900 秒（15 分鐘）

### 3.2 QR Code 掃碼驗證
- **RPC**: `validate_qr_plain(qr_plain)`
- **用途**: 商戶掃碼時驗證 QR 碼有效性
- **返回**: `card_id` (卡片 UUID)
- **錯誤碼**:
  - `INVALID_QR` - QR 碼格式不正確
  - `QR_EXPIRED_OR_INVALID` - QR 碼已過期或無效

### 3.3 QR Code 撤銷
- **RPC**: `revoke_card_qr(p_card_id, p_session_id)`
- **用途**: 立即使 QR 碼失效（卡片遺失或安全問題）
- **權限**: 與 `rotate_card_qr` 相同

---

## 4. 交易流程

### 4.1 支付
**RPC**: `merchant_charge_by_qr(p_merchant_code, p_qr_plain, p_raw_amount, p_idempotency_key, p_tag, p_external_order_id, p_session_id)`

**流程**:
1. 商戶 POS 掃描會員 QR → 得到 `qr_plain`
2. 調用 `merchant_charge_by_qr`
   - **權限檢查**: 驗證商戶身份（Super Admin 或 Merchant）
   - **QR 驗證**: `validate_qr_plain` → 得到 `card_id`
   - **併發鎖**: `pg_advisory_xact_lock(card_id)` → 鎖定卡片
   - **冒等檢查**: 檢查 `p_idempotency_key` 和 `p_external_order_id`
   - **折扣計算**:
     - Standard Card: `LEAST(積分折扣, 企業折扣)`
     - Corporate Card: 不能直接支付 → `CORPORATE_CARD_CANNOT_PAY`
     - Voucher Card: 無折扣
   - **餘額檢查**: `balance >= final_amount`
   - **交易記錄**: 插入 `transactions (payment)`
   - **更新卡片**: 更新 `balance`、`points`、`level`、`discount`
   - **積分記錄**: 寫入 `point_ledger`
   - **審計日誌**: 寫入 `audit.event_log`
3. 返回 `tx_id, tx_no, card_id, final_amount, discount`

**錯誤碼**:
- `INSUFFICIENT_BALANCE` - 餘額不足
- `QR_EXPIRED_OR_INVALID` - QR 碼過期或無效
- `NOT_AUTHORIZED_FOR_THIS_MERCHANT` - 沒有權限操作此商戶
- `CORPORATE_CARD_CANNOT_PAY` - 企業卡不能直接支付
- `CARD_NOT_ACTIVE` - 卡片未激活
- `CARD_EXPIRED` - 卡片已過期

### 4.2 退款
**RPC**: `merchant_refund_tx(p_merchant_code, p_original_tx_no, p_refund_amount, p_tag, p_session_id)`

**流程**:
1. 商戶輸入原交易號 `tx_no`
2. 調用 `merchant_refund_tx`
   - **權限檢查**: 驗證商戶身份（Super Admin 或 Merchant）
   - **交易驗證**: 驗證原交易屬於該商戶
   - **狀態檢查**: 狀態為 `completed` 或 `refunded`
   - **金額計算**: 計算剩餘可退金額
     - `remaining = original_amount - SUM(refunded_amounts)`
     - 支持多次部分退款
   - **退款處理**:
     - 插入 `transactions (refund)` 記錄
     - 更新卡片 `balance += refund_amount`
     - 若全額退款，更新原交易狀態為 `refunded`
   - **審計日誌**: 寫入 `audit.event_log`
3. 返回 `refund_tx_id, refund_tx_no, refunded_amount`

**退款規則**:
- 只能退款已完成的支付交易
- 支持多次部分退款
- 總退款金額 ≤ 原交易金額
- 退款不退還積分

**錯誤碼**:
- `ORIGINAL_TX_NOT_FOUND` - 原交易不存在
- `ONLY_COMPLETED_PAYMENT_REFUNDABLE` - 只能退款已完成的交易
- `REFUND_EXCEEDS_REMAINING` - 退款金額超過剩餘可退金額
- `NOT_AUTHORIZED_FOR_THIS_MERCHANT` - 沒有權限操作此商戶

### 4.3 充值
**RPC**: `user_recharge_card(p_card_id, p_amount, p_payment_method, p_tag, p_idempotency_key, p_external_order_id, p_session_id)`

**流程**:
1. 會員於 App 選擇卡片與金額
2. 調用第三方支付 → `external_order_id`
3. 調用 `user_recharge_card`
   - **卡片類型檢查**: 只有 Standard Card 可以充值
   - **冒等檢查**: 檢查 `p_idempotency_key` 和 `p_external_order_id`
   - **併發鎖**: `pg_advisory_xact_lock(card_id)`
   - **交易記錄**: 插入 `transactions (recharge)`
   - **更新餘額**: `balance += amount`
   - **審計日誌**: 寫入 `audit.event_log`
4. 返回 `tx_id, tx_no, card_id, amount`

**支付方式**: `wechat` | `alipay` | `cash` | `balance`

**卡片類型限制**:
- ✅ **Standard Card**: 可以充值
- ❌ **Corporate Card**: 不可充值（只提供折扣）
- ❌ **Voucher Card**: 不可充值（一次性使用）

**錯誤碼**:
- `INVALID_RECHARGE_AMOUNT` - 充值金額無效
- `CARD_NOT_FOUND_OR_INACTIVE` - 卡片不存在或未激活
- `UNSUPPORTED_CARD_TYPE_FOR_RECHARGE` - 卡片類型不支持充值

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
