-- ============================================================================
-- mps_test_rpc.sql - 測試專用 RPC 函數
-- 這些函數僅用於測試環境，不應在生產環境中使用
-- 包含測試數據管理和清理功能
-- 修改：適配新的認證體系（只有 super_admin，移除 admin）
-- ============================================================================

-- 注意：此文件包含的函數可能會刪除數據，請勿在生產環境使用！
-- 注意：這些函數需要 super_admin 權限才能執行

-- DROP EXISTING TEST FUNCTIONS
DROP FUNCTION IF EXISTS create_test_member(text, text, text) CASCADE;
DROP FUNCTION IF EXISTS create_test_member(text, text, text, text) CASCADE;
DROP FUNCTION IF EXISTS delete_test_member(uuid) CASCADE;
DROP FUNCTION IF EXISTS delete_test_merchant(uuid) CASCADE;
DROP FUNCTION IF EXISTS cleanup_test_data(text) CASCADE;
DROP FUNCTION IF EXISTS reset_test_environment() CASCADE;

-- 新增測試函數的 DROP 語句
DROP FUNCTION IF EXISTS create_test_merchant(text, text, text, text) CASCADE;
DROP FUNCTION IF EXISTS create_test_dataset(integer, integer, integer) CASCADE;
DROP FUNCTION IF EXISTS create_test_corporate_card(uuid, text, numeric, numeric) CASCADE;
DROP FUNCTION IF EXISTS create_test_voucher_card(uuid, text, numeric, timestamptz) CASCADE;

-- ============================================================================
-- TEST HELPER FUNCTIONS
-- ============================================================================

-- 創建測試會員（便捷包裝函數）
CREATE OR REPLACE FUNCTION create_test_member(
  p_name text DEFAULT 'Test User',
  p_phone text DEFAULT NULL,
  p_email text DEFAULT NULL,
  p_password text DEFAULT 'test123456'
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 使用商業 RPC 創建會員
  SELECT create_member_profile(
    p_name,
    p_phone,
    p_email,
    p_password,
    NULL,  -- binding_user_org
    NULL,  -- binding_org_id
    'standard'
  ) INTO v_member_id;
  
  RETURN v_member_id;
END;
$$;

COMMENT ON FUNCTION create_test_member IS '創建測試會員（便捷包裝，僅測試環境使用）';


-- 刪除測試會員（硬刪除）
CREATE OR REPLACE FUNCTION delete_test_member(
  p_member_id uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 按順序刪除相關記錄（避免外鍵約束）
  
  -- 1. 刪除積分記錄
  DELETE FROM point_ledger 
  WHERE card_id IN (SELECT id FROM member_cards WHERE owner_member_id = p_member_id);
  
  -- 2. 刪除交易記錄
  DELETE FROM transactions 
  WHERE card_id IN (SELECT id FROM member_cards WHERE owner_member_id = p_member_id);
  
  -- 3. 刪除 QR 歷史
  DELETE FROM card_qr_history 
  WHERE card_id IN (SELECT id FROM member_cards WHERE owner_member_id = p_member_id);
  
  -- 4. 刪除 QR 狀態
  DELETE FROM card_qr_state 
  WHERE card_id IN (SELECT id FROM member_cards WHERE owner_member_id = p_member_id);
  
  -- 5. 刪除卡片綁定
  DELETE FROM card_bindings 
  WHERE member_id = p_member_id 
     OR card_id IN (SELECT id FROM member_cards WHERE owner_member_id = p_member_id);
  
  -- 6. 刪除會員卡片
  DELETE FROM member_cards WHERE owner_member_id = p_member_id;
  
  -- 7. 刪除外部身份
  DELETE FROM member_external_identities WHERE member_id = p_member_id;
  
  -- 8. 最後刪除會員
  DELETE FROM member_profiles WHERE id = p_member_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'DELETE_TEST_MEMBER', 'member_profiles', p_member_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION delete_test_member IS '刪除測試會員（硬刪除，僅測試環境使用）';

-- 刪除測試商戶（硬刪除）
CREATE OR REPLACE FUNCTION delete_test_merchant(
  p_merchant_id uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 按順序刪除相關記錄（避免外鍵約束）
  
  -- 1. 刪除結算記錄
  DELETE FROM settlements WHERE merchant_id = p_merchant_id;
  
  -- 2. 刪除交易記錄
  DELETE FROM transactions WHERE merchant_id = p_merchant_id;
  
  -- 3. 刪除訂單註冊表
  DELETE FROM merchant_order_registry WHERE merchant_id = p_merchant_id;
  
  -- 4. 刪除商戶用戶關聯
  DELETE FROM merchant_users WHERE merchant_id = p_merchant_id;
  
  -- 5. 最後刪除商戶
  DELETE FROM merchants WHERE id = p_merchant_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'DELETE_TEST_MERCHANT', 'merchants', p_merchant_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION delete_test_merchant IS '刪除測試商戶（硬刪除，僅測試環境使用）';

-- 批量清理測試數據
CREATE OR REPLACE FUNCTION cleanup_test_data(
  p_name_pattern text DEFAULT '測試%'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_deleted_members int := 0;
  v_deleted_merchants int := 0;
  v_deleted_sessions int := 0;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');  -- 改為 super_admin
  
  -- 清理測試相關的 sessions
  WITH deleted AS (
    DELETE FROM app_sessions
    WHERE user_role IN ('merchant', 'member')
      AND (
        merchant_id IN (SELECT id FROM merchants WHERE name LIKE p_name_pattern)
        OR member_id IN (SELECT id FROM member_profiles WHERE name LIKE p_name_pattern)
      )
    RETURNING session_id
  )
  SELECT COUNT(*) INTO v_deleted_sessions FROM deleted;
  
  -- 刪除測試會員（會級聯刪除卡片和綁定）
  WITH deleted AS (
    DELETE FROM member_profiles
    WHERE name LIKE p_name_pattern
    RETURNING id
  )
  SELECT COUNT(*) INTO v_deleted_members FROM deleted;
  
  -- 刪除測試商戶
  WITH deleted AS (
    DELETE FROM merchants
    WHERE name LIKE p_name_pattern
    RETURNING id
  )
  SELECT COUNT(*) INTO v_deleted_merchants FROM deleted;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CLEANUP_TEST_DATA', 'system', NULL,
          jsonb_build_object(
            'deleted_members', v_deleted_members,
            'deleted_merchants', v_deleted_merchants,
            'deleted_sessions', v_deleted_sessions,
            'pattern', p_name_pattern
          ), now_utc());
  
  RETURN jsonb_build_object(
    'deleted_members', v_deleted_members,
    'deleted_merchants', v_deleted_merchants,
    'deleted_sessions', v_deleted_sessions,
    'success', true
  );
END;
$$;

COMMENT ON FUNCTION cleanup_test_data IS '批量清理測試數據（硬刪除，僅測試環境使用）';

-- 重置測試環境
CREATE OR REPLACE FUNCTION reset_test_environment()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_result jsonb;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');  -- 只有 super_admin 可以執行
  
  -- 清理所有測試數據
  v_result := cleanup_test_data('測試%');
  
  -- 重置序列（可選）
  -- ALTER SEQUENCE seq_member_no RESTART WITH 1;
  -- ALTER SEQUENCE seq_card_no RESTART WITH 1;
  -- ALTER SEQUENCE seq_tx_no RESTART WITH 1;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'RESET_TEST_ENVIRONMENT', 'system', NULL, v_result, now_utc());
  
  RETURN jsonb_build_object(
    'status', 'success',
    'message', '測試環境已重置',
    'details', v_result
  );
END;
$$;

COMMENT ON FUNCTION reset_test_environment IS '重置測試環境（僅 super_admin 可執行）';

-- =======================
-- 測試數據管理擴展函數
-- =======================

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

-- 創建測試企業卡（便捷包裝函數）
CREATE OR REPLACE FUNCTION create_test_corporate_card(
  p_owner_member_id uuid,
  p_name text DEFAULT NULL,
  p_initial_balance numeric(12,2) DEFAULT 0,
  p_fixed_discount numeric(4,3) DEFAULT NULL
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 使用商業 RPC 創建企業卡
  SELECT create_corporate_card(
    p_owner_member_id,
    p_name,
    p_initial_balance,
    p_fixed_discount
  ) INTO v_card_id;
  
  RETURN v_card_id;
END;
$$;

COMMENT ON FUNCTION create_test_corporate_card IS '創建測試企業卡（便捷包裝，僅測試環境使用）';

-- 創建測試代金券卡（便捷包裝函數）
CREATE OR REPLACE FUNCTION create_test_voucher_card(
  p_owner_member_id uuid,
  p_name text DEFAULT NULL,
  p_initial_balance numeric(12,2) DEFAULT 0,
  p_expires_at timestamptz DEFAULT NULL
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 使用商業 RPC 創建代金券卡
  SELECT create_voucher_card(
    p_owner_member_id,
    p_name,
    p_initial_balance,
    p_expires_at
  ) INTO v_card_id;
  
  RETURN v_card_id;
END;
$$;

COMMENT ON FUNCTION create_test_voucher_card IS '創建測試代金券卡（便捷包裝，僅測試環境使用）';

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
    v_corporate_card_id := create_test_corporate_card(
      ((v_member_ids->>i-1)->>'id')::uuid,
      'Test Corporate Card ' || i,
      1000.00,
      0.800  -- 8折
    );
    
    -- 設置綁定密碼
    PERFORM set_card_binding_password(v_corporate_card_id, 'test123456');
    
    -- 創建代金券卡
    v_card_id := create_test_voucher_card(
      ((v_member_ids->>i-1)->>'id')::uuid,
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

-- ============================================================================
-- END OF TEST RPC FILE
-- ============================================================================