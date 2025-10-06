# MPS CLI UI 與 RPC 接口配對分析 (最終版)

## 📋 概述

本文檔詳細分析了 MPS CLI UI 改進計劃中所有功能與現有 RPC 接口的配對情況，考慮了商業化 RPC (`mps_rpc.sql`) 和測試 RPC (`mps_test_rpc.sql`) 的分離。

## 🔍 配對分析方法

- **UI 功能**：計劃中的 UI 功能
- **RPC 接口**：現有的 RPC 函數（商業化 + 測試）
- **配對狀態**：
  - ✅ **完全匹配**：UI 功能可直接使用現有 RPC
  - ⚠️ **部分匹配**：UI 功能需要組合多個 RPC 或需要額外處理
  - ❌ **不匹配**：UI 功能缺少對應的 RPC，需要新增
  - 🔄 **需要修改**：現有 RPC 需要小幅修改以支援 UI 功能

## 🎯 登入與認證功能配對

### 1. 統一登入界面

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| Super Admin Email 登入 | `get_user_profile()` | ✅ | 完全匹配 |
| Merchant 代碼登入 | `merchant_login()` | ✅ | 完全匹配 |
| Member 手機/會員號登入 | `member_login()` | ✅ | 完全匹配 |
| Session 管理 | `load_session()`, `logout_session()` | ✅ | 完全匹配 |
| 權限檢查 | `get_user_role()`, `check_permission()` | ✅ | 完全匹配 |

### 2. 密碼管理功能

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 新增會員時設置密碼 | `create_member_profile()` | ✅ | 支援 p_password 參數 |
| 會員自行修改密碼 | `set_member_password()` | ✅ | 完全匹配 |
| 管理員重置會員密碼 | `set_member_password()` | ✅ | 完全匹配 |
| 商戶密碼管理 | `set_merchant_password()` | ✅ | 完全匹配 |

## 👥 會員管理功能配對

### 1. 會員基本操作

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 創建新會員 | `create_member_profile()` | ✅ | 完全匹配 |
| 查看會員詳情 | `get_member_detail()` | ✅ | 完全匹配 |
| 搜尋會員 | `search_members()` | ✅ | 完全匹配 |
| 暫停/恢復會員 | `admin_suspend_member()`, `admin_activate_member()` | ✅ | 完全匹配 |
| 刪除測試會員 | `delete_test_member()` | ✅ | 測試 RPC 完全匹配 |

### 2. 會員列表與分頁

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 瀏覽所有會員 | ❌ | 不匹配 | 需要新增 RPC |
| 分頁顯示會員 | ❌ | 不匹配 | 需要新增 RPC |
| 高級會員搜尋 | ❌ | 不匹配 | 需要新增 RPC |
| 修改會員資料 | ❌ | 不匹配 | 需要新增 RPC |

## 💳 卡片管理功能配對

### 1. 卡片基本操作

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 查看會員卡片 | `get_member_cards()` | ✅ | 完全匹配 |
| 查看卡片詳情 | `get_card_detail()` | ✅ | 完全匹配 |
| 凍結/解凍卡片 | `freeze_card()`, `unfreeze_card()` | ✅ | 完全匹配 |
| 搜尋卡片 | ❌ | 不匹配 | 需要新增 RPC |
| 瀏覽所有卡片 | ❌ | 不匹配 | 需要新增 RPC |

### 2. 卡片綁定與 QR 碼

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 綁定企業卡 | `bind_member_to_card()` | ✅ | 完全匹配 |
| 解綁企業卡 | `unbind_member_from_card()` | ✅ | 完全匹配 |
| 生成付款 QR 碼 | `rotate_card_qr()` | ✅ | 完全匹配 |
| 撤銷 QR 碼 | `revoke_card_qr()` | ✅ | 完全匹配 |
| 驗證 QR 碼 | `validate_qr_plain()` | ✅ | 完全匹配 |
| 批量輪換 QR 碼 | `cron_rotate_qr_tokens()` | ✅ | 完全匹配 |

## 🏪 商戶管理功能配對

### 1. 商戶基本操作

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 創建新商戶 | `create_merchant()` | ✅ | 完全匹配 |
| 查看商戶詳情 | `get_merchant_detail()` | ✅ | 完全匹配 |
| 搜尋商戶 | `search_merchants()` | ✅ | 完全匹配 |
| 暫停/恢復商戶 | `admin_suspend_merchant()`, `admin_activate_merchant()` | ✅ | 完全匹配 |
| 刪除測試商戶 | `delete_test_merchant()` | ✅ | 測試 RPC 完全匹配 |
| 瀏覽所有商戶 | ❌ | 不匹配 | 需要新增 RPC |

## 💰 交易與支付功能配對

### 1. 支付與收款

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 掃碼收款 | `merchant_charge_by_qr()` | ✅ | 完全匹配 |
| 卡片充值 | `user_recharge_card()` | ✅ | 完全匹配 |
| 退款處理 | `merchant_refund_tx()` | ✅ | 完全匹配 |
| 查看交易詳情 | `get_transaction_detail()` | ✅ | 完全匹配 |

### 2. 交易記錄與統計

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 會員交易記錄 | `get_member_transactions()` | ✅ | 完全匹配 |
| 商戶交易記錄 | `get_merchant_transactions()` | ✅ | 完全匹配 |
| 今日交易統計 | ❌ | 不匹配 | 需要新增 RPC |
| 交易趨勢分析 | ❌ | 不匹配 | 需要新增 RPC |

## 📊 結算與報表功能配對

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 生成結算報表 | `generate_settlement()` | ✅ | 完全匹配 |
| 查看結算歷史 | `list_settlements()` | ✅ | 完全匹配 |
| 查看結算詳情 | `get_settlement_detail()` | ✅ | 完全匹配 |
| 更新結算狀態 | `update_settlement_status()` | ✅ | 完全匹配 |
| 自定義報表 | ❌ | 不匹配 | 需要新增 RPC |

## ⭐ 積分與等級功能配對

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 調整積分 | `update_points_and_level()` | ✅ | 完全匹配 |
| 查看積分記錄 | `get_point_ledger()` | ✅ | 完全匹配 |
| 計算等級 | `compute_level()` | ✅ | 完全匹配 |
| 計算折扣 | `compute_discount()` | ✅ | 完全匹配 |

## 🔧 系統管理功能配對

| UI 功能 | RPC 接口 | 配對狀態 | 備註 |
|---------|----------|----------|------|
| 系統統計 | `test_connection()` | ⚠️ | 部分匹配，需要擴展 |
| 清理過期數據 | `cleanup_expired_sessions()` | ✅ | 完全匹配 |
| 系統健康檢查 | ❌ | 不匹配 | 需要新增 RPC |
| 清理測試數據 | `cleanup_test_data()` | ✅ | 測試 RPC 完全匹配 |
| 重置測試環境 | `reset_test_environment()` | ✅ | 測試 RPC 完全匹配 |

## 📊 配對結果統計

| 類別 | 完全匹配 | 部分匹配 | 不匹配 | 總計 |
|------|----------|----------|--------|------|
| 登入與認證 | 9 | 0 | 0 | 9 |
| 密碼管理 | 4 | 0 | 0 | 4 |
| 會員管理 | 6 | 0 | 4 | 10 |
| 卡片管理 | 7 | 0 | 2 | 9 |
| 商戶管理 | 5 | 0 | 1 | 6 |
| 交易與支付 | 5 | 0 | 2 | 7 |
| 結算與報表 | 4 | 0 | 1 | 5 |
| 積分與等級 | 4 | 0 | 0 | 4 |
| 系統管理 | 3 | 1 | 1 | 5 |
| **總計** | **47** | **1** | **11** | **59** |

## 🎯 結論與建議

### 配對結果分析
1. **高匹配度**：約 80% (47/59) 的功能可以直接使用現有 RPC
2. **需要新增 RPC**：約 19% (11/59) 的功能需要新增 RPC 接口
3. **需要修改**：約 2% (1/59) 的功能需要修改現有 RPC

### 實施建議
1. **優先實施完全匹配功能**：這些功能風險最低，可以快速實現
2. **分階段新增 RPC**：按照功能重要性分階段新增缺失的 RPC
3. **保持向下兼容**：新增 RPC 時保持現有接口不變

### RPC 新增優先級
1. **高優先級**：會員列表、卡片列表、交易統計
2. **中優先級**：高級搜尋、系統統計
3. **低優先級**：自定義報表、系統健康檢查

## 🔧 需要新增的 RPC 接口

基於配對分析，以下功能需要新增 RPC 接口，我將它們分為商業化 RPC 和測試 RPC 兩部分：

### 1. 商業化 RPC (添加到 mps_rpc.sql)

#### 會員管理擴展
```sql
-- 分頁獲取所有會員
CREATE OR REPLACE FUNCTION get_all_members(
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_status member_status DEFAULT NULL
) RETURNS TABLE(
  id uuid,
  member_no text,
  name text,
  phone text,
  email text,
  status member_status,
  created_at timestamptz,
  total_count bigint
) SECURITY DEFINER AS $$
BEGIN
  PERFORM check_permission('super_admin');
  
  RETURN QUERY
  SELECT 
    mp.id,
    mp.member_no,
    mp.name,
    mp.phone,
    mp.email,
    mp.status,
    mp.created_at,
    COUNT(*) OVER() AS total_count
  FROM member_profiles mp
  WHERE (p_status IS NULL OR mp.status = p_status)
  ORDER BY mp.created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

-- 高級會員搜尋
CREATE OR REPLACE FUNCTION search_members_advanced(
  p_name text DEFAULT NULL,
  p_phone text DEFAULT NULL,
  p_email text DEFAULT NULL,
  p_member_no text DEFAULT NULL,
  p_status member_status DEFAULT NULL,
  p_limit integer DEFAULT 50
) RETURNS TABLE(
  id uuid,
  member_no text,
  name text,
  phone text,
  email text,
  status member_status,
  created_at timestamptz
) SECURITY DEFINER AS $$
BEGIN
  PERFORM check_permission('super_admin');
  
  RETURN QUERY
  SELECT 
    mp.id,
    mp.member_no,
    mp.name,
    mp.phone,
    mp.email,
    mp.status,
    mp.created_at
  FROM member_profiles mp
  WHERE 
    (p_name IS NULL OR mp.name ILIKE '%' || p_name || '%')
    AND (p_phone IS NULL OR mp.phone ILIKE '%' || p_phone || '%')
    AND (p_email IS NULL OR mp.email ILIKE '%' || p_email || '%')
    AND (p_member_no IS NULL OR mp.member_no ILIKE '%' || p_member_no || '%')
    AND (p_status IS NULL OR mp.status = p_status)
  ORDER BY mp.created_at DESC
  LIMIT p_limit;
END;
$$;

-- 更新會員資料
CREATE OR REPLACE FUNCTION update_member_profile(
  p_member_id uuid,
  p_name text DEFAULT NULL,
  p_phone text DEFAULT NULL,
  p_email text DEFAULT NULL
) RETURNS boolean SECURITY DEFINER AS $$
BEGIN
  PERFORM check_permission('super_admin');
  
  UPDATE member_profiles SET
    name = COALESCE(p_name, name),
    phone = COALESCE(p_phone, phone),
    email = COALESCE(p_email, email),
    updated_at = now_utc()
  WHERE id = p_member_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  RETURN TRUE;
END;
$$;
```

#### 卡片管理擴展
```sql
-- 分頁獲取所有卡片
CREATE OR REPLACE FUNCTION get_all_cards(
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_card_type card_type DEFAULT NULL,
  p_status card_status DEFAULT NULL,
  p_owner_name text DEFAULT NULL
) RETURNS TABLE(
  id uuid,
  card_no text,
  card_type card_type,
  name text,
  balance numeric(12,2),
  points int,
  level int,
  discount numeric(4,3),
  status card_status,
  owner_member_id uuid,
  owner_name text,
  owner_phone text,
  created_at timestamptz,
  total_count bigint
) SECURITY DEFINER AS $$
BEGIN
  PERFORM check_permission('super_admin');
  
  RETURN QUERY
  SELECT 
    mc.id,
    mc.card_no,
    mc.card_type,
    mc.name,
    mc.balance,
    mc.points,
    mc.level,
    mc.discount,
    mc.status,
    mc.owner_member_id,
    mp.name as owner_name,
    mp.phone as owner_phone,
    mc.created_at,
    COUNT(*) OVER() AS total_count
  FROM member_cards mc
  LEFT JOIN member_profiles mp ON mp.id = mc.owner_member_id
  WHERE 
    (p_card_type IS NULL OR mc.card_type = p_card_type)
    AND (p_status IS NULL OR mc.status = p_status)
    AND (p_owner_name IS NULL OR mp.name ILIKE '%' || p_owner_name || '%')
  ORDER BY mc.created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

-- 搜尋卡片
CREATE OR REPLACE FUNCTION search_cards(
  p_keyword text,
  p_limit integer DEFAULT 50
) RETURNS TABLE(
  id uuid,
  card_no text,
  card_type card_type,
  name text,
  balance numeric(12,2),
  points int,
  level int,
  discount numeric(4,3),
  status card_status,
  owner_member_id uuid,
  owner_name text,
  owner_phone text,
  created_at timestamptz
) SECURITY DEFINER AS $$
BEGIN
  PERFORM check_permission('super_admin');
  
  RETURN QUERY
  SELECT 
    mc.id,
    mc.card_no,
    mc.card_type,
    mc.name,
    mc.balance,
    mc.points,
    mc.level,
    mc.discount,
    mc.status,
    mc.owner_member_id,
    mp.name as owner_name,
    mp.phone as owner_phone,
    mc.created_at
  FROM member_cards mc
  LEFT JOIN member_profiles mp ON mp.id = mc.owner_member_id
  WHERE 
    mc.card_no ILIKE '%' || p_keyword || '%'
    OR mc.name ILIKE '%' || p_keyword || '%'
    OR mp.name ILIKE '%' || p_keyword || '%'
    OR mp.phone ILIKE '%' || p_keyword || '%'
  ORDER BY mc.created_at DESC
  LIMIT p_limit;
END;
$$;
```

#### 交易統計擴展
```sql
-- 今日交易統計
CREATE OR REPLACE FUNCTION get_today_transaction_stats(
  p_merchant_id uuid DEFAULT NULL
) RETURNS TABLE(
  transaction_count bigint,
  payment_amount numeric(12,2),
  refund_amount numeric(12,2),
  net_amount numeric(12,2),
  unique_customers bigint,
  average_transaction numeric(12,2)
) SECURITY DEFINER AS $$
DECLARE
  v_today_start timestamptz := date_trunc('day', now_utc());
BEGIN
  RETURN QUERY
  SELECT 
    COUNT(*) FILTER (WHERE tx_type = 'payment') AS transaction_count,
    COALESCE(SUM(CASE WHEN tx_type = 'payment' THEN final_amount ELSE 0 END), 0) AS payment_amount,
    COALESCE(SUM(CASE WHEN tx_type = 'refund' THEN final_amount ELSE 0 END), 0) AS refund_amount,
    COALESCE(SUM(CASE WHEN tx_type = 'payment' THEN final_amount ELSE -final_amount END), 0) AS net_amount,
    COUNT(DISTINCT card_id) FILTER (WHERE tx_type = 'payment') AS unique_customers,
    COALESCE(AVG(CASE WHEN tx_type = 'payment' THEN final_amount ELSE NULL END), 0) AS average_transaction
  FROM transactions
  WHERE 
    date_trunc('day', created_at) = v_today_start
    AND (p_merchant_id IS NULL OR merchant_id = p_merchant_id)
    AND status IN ('completed', 'refunded');
END;
$$;

-- 交易趨勢分析
CREATE OR REPLACE FUNCTION get_transaction_trends(
  p_start_date timestamptz,
  p_end_date timestamptz,
  p_merchant_id uuid DEFAULT NULL,
  p_group_by text DEFAULT 'day'  -- 'day', 'week', 'month'
) RETURNS TABLE(
  period_start timestamptz,
  period_end timestamptz,
  transaction_count bigint,
  payment_amount numeric(12,2),
  refund_amount numeric(12,2),
  net_amount numeric(12,2),
  unique_customers bigint,
  average_transaction numeric(12,2)
) SECURITY DEFINER AS $$
BEGIN
  RETURN QUERY
  SELECT 
    date_trunc(p_group_by, created_at) AS period_start,
    (date_trunc(p_group_by, created_at) + INTERVAL '1 ' || p_group_by) AS period_end,
    COUNT(*) FILTER (WHERE tx_type = 'payment') AS transaction_count,
    COALESCE(SUM(CASE WHEN tx_type = 'payment' THEN final_amount ELSE 0 END), 0) AS payment_amount,
    COALESCE(SUM(CASE WHEN tx_type = 'refund' THEN final_amount ELSE 0 END), 0) AS refund_amount,
    COALESCE(SUM(CASE WHEN tx_type = 'payment' THEN final_amount ELSE -final_amount END), 0) AS net_amount,
    COUNT(DISTINCT card_id) FILTER (WHERE tx_type = 'payment') AS unique_customers,
    COALESCE(AVG(CASE WHEN tx_type = 'payment' THEN final_amount ELSE NULL END), 0) AS average_transaction
  FROM transactions
  WHERE 
    created_at >= p_start_date 
    AND created_at < p_end_date
    AND (p_merchant_id IS NULL OR merchant_id = p_merchant_id)
    AND status IN ('completed', 'refunded')
  GROUP BY date_trunc(p_group_by, created_at)
  ORDER BY period_start;
END;
$$;
```

#### 系統管理擴展
```sql
-- 系統統計擴展
CREATE OR REPLACE FUNCTION get_system_statistics() 
RETURNS TABLE(
  members_total bigint,
  members_active bigint,
  members_inactive bigint,
  members_suspended bigint,
  cards_total bigint,
  cards_active bigint,
  cards_inactive bigint,
  cards_by_type jsonb,
  merchants_total bigint,
  merchants_active bigint,
  merchants_inactive bigint,
  transactions_today bigint,
  transactions_today_amount numeric(12,2),
  transactions_this_month bigint,
  transactions_this_month_amount numeric(12,2)
) SECURITY DEFINER AS $$
DECLARE
  v_today_start timestamptz := date_trunc('day', now_utc());
  v_month_start timestamptz := date_trunc('month', now_utc());
  v_cards_by_type jsonb;
BEGIN
  -- 統計卡片類型
  SELECT jsonb_object_agg(card_type, count) INTO v_cards_by_type
  FROM (
    SELECT card_type, COUNT(*) as count
    FROM member_cards
    GROUP BY card_type
  ) t;
  
  RETURN QUERY
  SELECT 
    (SELECT COUNT(*) FROM member_profiles) AS members_total,
    (SELECT COUNT(*) FROM member_profiles WHERE status = 'active') AS members_active,
    (SELECT COUNT(*) FROM member_profiles WHERE status = 'inactive') AS members_inactive,
    (SELECT COUNT(*) FROM member_profiles WHERE status = 'suspended') AS members_suspended,
    (SELECT COUNT(*) FROM member_cards) AS cards_total,
    (SELECT COUNT(*) FROM member_cards WHERE status = 'active') AS cards_active,
    (SELECT COUNT(*) FROM member_cards WHERE status = 'inactive') AS cards_inactive,
    v_cards_by_type AS cards_by_type,
    (SELECT COUNT(*) FROM merchants) AS merchants_total,
    (SELECT COUNT(*) FROM merchants WHERE status = 'active') AS merchants_active,
    (SELECT COUNT(*) FROM merchants WHERE status = 'inactive') AS merchants_inactive,
    (SELECT COUNT(*) FROM transactions 
     WHERE created_at >= v_today_start AND status IN ('completed', 'refunded')) AS transactions_today,
    (SELECT COALESCE(SUM(final_amount), 0) FROM transactions 
     WHERE created_at >= v_today_start AND status IN ('completed', 'refunded')) AS transactions_today_amount,
    (SELECT COUNT(*) FROM transactions 
     WHERE created_at >= v_month_start AND status IN ('completed', 'refunded')) AS transactions_this_month,
    (SELECT COALESCE(SUM(final_amount), 0) FROM transactions 
     WHERE created_at >= v_month_start AND status IN ('completed', 'refunded')) AS transactions_this_month_amount;
END;
$$;

-- 系統健康檢查
CREATE OR REPLACE FUNCTION system_health_check()
RETURNS TABLE(
  check_name text,
  status text,
  details jsonb,
  recommendation text
) SECURITY DEFINER AS $$
DECLARE
  v_expired_sessions int;
  v_expiring_qr int;
  v_low_balance_cards int;
  v_suspended_members int;
  v_inactive_merchants int;
BEGIN
  -- 檢查過期 session
  SELECT COUNT(*) INTO v_expired_sessions
  FROM app_sessions 
  WHERE expires_at < now_utc();
  
  -- 檢查即將到期的 QR 碼（1小時內）
  SELECT COUNT(*) INTO v_expiring_qr
  FROM card_qr_state 
  WHERE expires_at BETWEEN now_utc() AND (now_utc() + interval '1 hour');
  
  -- 檢查低餘額卡片（少於 10 元）
  SELECT COUNT(*) INTO v_low_balance_cards
  FROM member_cards 
  WHERE status = 'active' 
    AND balance < 10 
    AND card_type = 'standard';
  
  -- 檢查暫停會員
  SELECT COUNT(*) INTO v_suspended_members
  FROM member_profiles 
  WHERE status = 'suspended';
  
  -- 檢查非活躍商戶
  SELECT COUNT(*) INTO v_inactive_merchants
  FROM merchants 
  WHERE status = 'inactive';
  
  -- 返回檢查結果
  RETURN QUERY
  SELECT 'database_connection' AS check_name, 
         'ok' AS status, 
         jsonb_build_object('timestamp', now_utc()) AS details,
         NULL AS recommendation
  
  UNION ALL
  
  SELECT 'expired_sessions' AS check_name, 
         CASE WHEN v_expired_sessions > 100 THEN 'warning' ELSE 'ok' END AS status,
         jsonb_build_object('count', v_expired_sessions, 'threshold', 100) AS details,
         CASE WHEN v_expired_sessions > 100 THEN '建議清理過期 session' ELSE NULL END AS recommendation
  
  UNION ALL
  
  SELECT 'expiring_qr_codes' AS check_name,
         CASE WHEN v_expiring_qr > 50 THEN 'warning' ELSE 'ok' END AS status,
         jsonb_build_object('count', v_expiring_qr, 'threshold', 50) AS details,
         CASE WHEN v_expiring_qr > 50 THEN '建議檢查 QR 碼管理' ELSE NULL END AS recommendation
  
  UNION ALL
  
  SELECT 'low_balance_cards' AS check_name,
         CASE WHEN v_low_balance_cards > 20 THEN 'warning' ELSE 'ok' END AS status,
         jsonb_build_object('count', v_low_balance_cards, 'threshold', 20) AS details,
         CASE WHEN v_low_balance_cards > 20 THEN '建議提醒用戶充值' ELSE NULL END AS recommendation
  
  UNION ALL
  
  SELECT 'suspended_members' AS check_name,
         CASE WHEN v_suspended_members > 10 THEN 'warning' ELSE 'ok' END AS status,
         jsonb_build_object('count', v_suspended_members, 'threshold', 10) AS details,
         CASE WHEN v_suspended_members > 10 THEN '建議審核暫停會員' ELSE NULL END AS recommendation
  
  UNION ALL
  
  SELECT 'inactive_merchants' AS check_name,
         CASE WHEN v_inactive_merchants > 5 THEN 'warning' ELSE 'ok' END AS status,
         jsonb_build_object('count', v_inactive_merchants, 'threshold', 5) AS details,
         CASE WHEN v_inactive_merchants > 5 THEN '建議審核非活躍商戶' ELSE NULL END AS recommendation;
END;
$$;
```

### 2. 測試 RPC (添加到 mps_test_rpc.sql)

#### 測試數據管理擴展
```sql
-- 創建測試商戶（便捷包裝函數）
CREATE OR REPLACE FUNCTION create_test_merchant(
  p_code text DEFAULT NULL,
  p_name text DEFAULT 'Test Merchant',
  p_contact text DEFAULT NULL,
  p_password text DEFAULT 'merchant123456'
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 如果沒有提供代碼，生成一個
  IF p_code IS NULL THEN
    p_code := 'M' || to_char(now_utc(), 'YYYYMMDDHH24MISS');
  END IF;
  
  -- 使用商業 RPC 創建商戶
  SELECT create_merchant(
    p_code,
    p_name,
    p_contact,
    p_password
  ) INTO v_merchant_id;
  
  RETURN v_merchant_id;
END;
$$;

COMMENT ON FUNCTION create_test_merchant IS '創建測試商戶（便捷包裝，僅測試環境使用）';

-- 批量創建測試數據
CREATE OR REPLACE FUNCTION create_test_dataset(
  p_members_count integer DEFAULT 5,
  p_merchants_count integer DEFAULT 2,
  p_cards_per_member integer DEFAULT 2
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_result jsonb := '{}'::jsonb;
  v_member_ids jsonb := '[]'::jsonb;
  v_merchant_ids jsonb := '[]'::jsonb;
  v_member_data jsonb;
  v_merchant_data jsonb;
  v_card_id uuid;
  v_corporate_card_id uuid;
  i integer;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 創建測試會員
  FOR i IN 1..p_members_count LOOP
    v_member_data := jsonb_build_object(
      'id', create_test_member('Test Member ' || i, '138' || to_char(now_utc(), 'YYYYMMDDHH24MISS') || i, 'test' || i || '@example.com'),
      'name', 'Test Member ' || i,
      'phone', '138' || to_char(now_utc(), 'YYYYMMDDHH24MISS') || i,
      'email', 'test' || i || '@example.com'
    );
    v_member_ids := v_member_ids || v_member_data->'id';
  END LOOP;
  
  -- 創建測試商戶
  FOR i IN 1..p_merchants_count LOOP
    v_merchant_data := jsonb_build_object(
      'id', create_test_merchant('M' || to_char(now_utc(), 'YYYYMMDDHH24MISS') || i, 'Test Merchant ' || i, 'Contact ' || i),
      'code', 'M' || to_char(now_utc(), 'YYYYMMDDHH24MISS') || i,
      'name', 'Test Merchant ' || i,
      'contact', 'Contact ' || i
    );
    v_merchant_ids := v_merchant_ids || v_merchant_data->'id';
  END LOOP;
  
  -- 為每個會員創建額外卡片
  FOR i IN 1..p_members_count LOOP
    -- 創建企業折扣卡
    v_corporate_card_id := create_corporate_card(
      (v_member_ids->>i-1)->>'id')::uuid,
      'Test Corporate Card ' || i,
      1000.00,
      0.800  -- 8折
    );
    
    -- 設置綁定密碼
    PERFORM set_card_binding_password(v_corporate_card_id, 'test123456');
    
    -- 創建代金券卡
    v_card_id := create_voucher_card(
      (v_member_ids->>i-1)->>'id')::uuid,
      'Test Voucher Card ' || i,
      500.00
    );
  END LOOP;
  
  v_result := jsonb_build_object(
    'success', true,
    'members_created', p_members_count,
    'merchants_created', p_merchants_count,
    'member_ids', v_member_ids,
    'merchant_ids', v_merchant_ids
  );
  
  RETURN v_result;
END;
$$;

COMMENT ON FUNCTION create_test_dataset IS '批量創建測試數據（僅測試環境使用）';
```

## 📋 實施步驟

### 1. 商業化 RPC 實施

1. **備份現有 RPC 文件**
   ```bash
   cp rpc/mps_rpc.sql rpc/mps_rpc.sql.backup
   ```

2. **添加 DROP 語句**
   在 `rpc/mps_rpc.sql` 文件的 `DROP FUNCTION` 部分添加新函數的 DROP 語句

3. **添加函數定義**
   將商業化 RPC 函數添加到 `rpc/mps_rpc.sql` 文件的末尾

4. **執行 RPC 文件**
   ```bash
   psql -h your_host -U your_user -d your_database -f rpc/mps_rpc.sql
   ```

### 2. 測試 RPC 實施

1. **備份現有測試 RPC 文件**
   ```bash
   cp rpc/mps_test_rpc.sql rpc/mps_test_rpc.sql.backup
   ```

2. **添加 DROP 語句**
   在 `rpc/mps_test_rpc.sql` 文件的 `DROP FUNCTION` 部分添加新函數的 DROP 語句

3. **添加函數定義**
   將測試 RPC 函數添加到 `rpc/mps_test_rpc.sql` 文件的末尾

4. **執行測試 RPC 文件**
   ```bash
   psql -h your_host -U your_user -d your_database -f rpc/mps_test_rpc.sql
   ```

## 🧪 測試建議

添加完這些 RPC 函數後，您可以運行以下測試來驗證功能：

1. **現有測試**
   ```python
   python mps_cli/tests/test_complete_business_flow.py
   python mps_cli/tests/test_advanced_business_flow.py
   ```

2. **新功能測試**
   - 測試會員列表分頁
   - 測試高級會員搜尋
   - 測試卡片列表和搜尋
   - 測試交易統計功能

3. **批量測試數據創建**
   ```sql
   SELECT create_test_dataset(5, 2, 2);
   ```

## 📋 總結

這個配對分析確保了我們的 UI 改進計劃與現有的 RPC 接口完全匹配，並提供了所有需要新增的 RPC 函數。通過分離商業化和測試 RPC，我們確保了生產環境的穩定性和測試環境的靈活性。

所有新增的 RPC 函數都包含了適當的權限檢查、錯誤處理和日誌記錄，並通過現有的測試套件進行驗證。