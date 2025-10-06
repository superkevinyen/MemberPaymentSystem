-- ============================================================================
-- MPS Identifier-Based RPC Functions
-- 支持通過業務識別碼（會員號、卡號、手機號等）進行查詢和操作
-- ============================================================================

-- 通過識別碼獲取會員
CREATE OR REPLACE FUNCTION get_member_by_identifier(
  p_identifier text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member member_profiles%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 支持 member_no, phone, email
  SELECT * INTO v_member
  FROM member_profiles
  WHERE member_no = p_identifier
     OR phone = p_identifier
     OR email = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  RETURN row_to_json(v_member)::jsonb;
END;
$$;

COMMENT ON FUNCTION get_member_by_identifier IS '通過識別碼獲取會員（支持會員號、手機號、郵箱）';

-- 通過識別碼獲取卡片
CREATE OR REPLACE FUNCTION get_card_by_identifier(
  p_identifier text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 支持 card_no
  SELECT * INTO v_card
  FROM member_cards
  WHERE card_no = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND';
  END IF;
  
  RETURN row_to_json(v_card)::jsonb;
END;
$$;

COMMENT ON FUNCTION get_card_by_identifier IS '通過卡號獲取卡片';

-- 通過識別碼獲取商戶
CREATE OR REPLACE FUNCTION get_merchant_by_identifier(
  p_identifier text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant merchants%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 支持 merchant_code
  SELECT * INTO v_merchant
  FROM merchants
  WHERE code = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  RETURN row_to_json(v_merchant)::jsonb;
END;
$$;

COMMENT ON FUNCTION get_merchant_by_identifier IS '通過商戶代碼獲取商戶';

-- 通過卡號獲取卡片詳情（包含持卡人信息）
CREATE OR REPLACE FUNCTION get_card_details_by_card_no(
  p_card_no text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_result jsonb;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 獲取卡片及持卡人信息
  SELECT jsonb_build_object(
    'id', mc.id,
    'card_no', mc.card_no,
    'card_type', mc.card_type,
    'name', mc.name,
    'balance', mc.balance,
    'points', mc.points,
    'level', mc.level,
    'discount', mc.discount,
    'fixed_discount', mc.fixed_discount,
    'status', mc.status,
    'expires_at', mc.expires_at,
    'created_at', mc.created_at,
    'updated_at', mc.updated_at,
    'owner_member_id', mc.owner_member_id,
    'owner_name', mp.name,
    'owner_phone', mp.phone,
    'owner_email', mp.email
  ) INTO v_result
  FROM member_cards mc
  LEFT JOIN member_profiles mp ON mp.id = mc.owner_member_id
  WHERE mc.card_no = p_card_no
  LIMIT 1;
  
  IF v_result IS NULL THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND';
  END IF;
  
  RETURN v_result;
END;
$$;

COMMENT ON FUNCTION get_card_details_by_card_no IS '通過卡號獲取卡片詳情（包含持卡人信息）';

-- 通過卡號凍結/解凍卡片
CREATE OR REPLACE FUNCTION toggle_card_status_by_card_no(
  p_card_no text,
  p_new_status card_status
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 通過卡號找到卡片 ID
  SELECT id INTO v_card_id
  FROM member_cards
  WHERE card_no = p_card_no
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND';
  END IF;
  
  -- 更新狀態
  UPDATE member_cards
  SET
    status = p_new_status,
    updated_at = now_utc()
  WHERE id = v_card_id;
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION toggle_card_status_by_card_no IS '通過卡號凍結/解凍卡片';

-- 通過識別碼更新會員資料
CREATE OR REPLACE FUNCTION update_member_by_identifier(
  p_identifier text,
  p_name text DEFAULT NULL,
  p_phone text DEFAULT NULL,
  p_email text DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 先通過識別碼找到 UUID
  SELECT id INTO v_member_id
  FROM member_profiles
  WHERE member_no = p_identifier
     OR phone = p_identifier
     OR email = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 執行更新
  UPDATE member_profiles
  SET
    name = COALESCE(p_name, name),
    phone = COALESCE(p_phone, phone),
    email = COALESCE(p_email, email),
    updated_at = now_utc()
  WHERE id = v_member_id;
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION update_member_by_identifier IS '通過識別碼更新會員資料';

-- 通過識別碼設置會員密碼
CREATE OR REPLACE FUNCTION set_member_password_by_identifier(
  p_identifier text,
  p_new_password text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id uuid;
  v_password_hash text;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 先通過識別碼找到 UUID
  SELECT id INTO v_member_id
  FROM member_profiles
  WHERE member_no = p_identifier
     OR phone = p_identifier
     OR email = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 加密密碼
  v_password_hash := extensions.crypt(p_new_password, extensions.gen_salt('bf'));
  
  -- 更新密碼
  UPDATE member_profiles
  SET
    password_hash = v_password_hash,
    updated_at = now_utc()
  WHERE id = v_member_id;
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION set_member_password_by_identifier IS '通過識別碼設置會員密碼';

-- 通過識別碼暫停/激活會員
CREATE OR REPLACE FUNCTION toggle_member_status_by_identifier(
  p_identifier text,
  p_new_status member_status
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 先通過識別碼找到 UUID
  SELECT id INTO v_member_id
  FROM member_profiles
  WHERE member_no = p_identifier
     OR phone = p_identifier
     OR email = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 更新狀態
  UPDATE member_profiles
  SET
    status = p_new_status,
    updated_at = now_utc()
  WHERE id = v_member_id;
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION toggle_member_status_by_identifier IS '通過識別碼暫停/激活會員';

-- ============================================================================
-- END OF IDENTIFIER RPC FILE
-- ============================================================================
