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

-- ============================================================================
-- END OF TEST RPC FILE
-- ============================================================================