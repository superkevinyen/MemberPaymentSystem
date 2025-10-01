-- ============================================================================
-- mps_rpc.sql  (Commercial Edition) - PUBLIC SCHEMA VERSION
-- All RPCs are SECURITY DEFINER. Re-run safe: we drop then create.
-- Assumes schemas/tables from mps_schema.sql already exist.
-- 修改：所有引用改為 public schema，添加 RLS 兼容性，新增認證函數
-- ============================================================================

-- 0) ENABLE REQUIRED EXTENSIONS (啟用必要的擴展)
-- pgcrypto: 用於密碼加密 (gen_salt, crypt 函數)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) DROP ALL EXISTING FUNCTIONS (清除所有現有函數以重新建立)
DROP FUNCTION IF EXISTS test_connection() CASCADE;
DROP FUNCTION IF EXISTS get_merchant_by_auth_user() CASCADE;
DROP FUNCTION IF EXISTS get_member_cards(uuid) CASCADE;
DROP FUNCTION IF EXISTS get_member_by_auth_user() CASCADE;
DROP FUNCTION IF EXISTS get_transaction_detail(text) CASCADE;
DROP FUNCTION IF EXISTS get_merchant_transactions(uuid, integer, integer, timestamptz, timestamptz) CASCADE;
DROP FUNCTION IF EXISTS get_member_transactions(uuid, integer, integer, timestamptz, timestamptz) CASCADE;
DROP FUNCTION IF EXISTS list_settlements(uuid, integer, integer) CASCADE;
DROP FUNCTION IF EXISTS generate_settlement(uuid, settlement_mode, timestamptz, timestamptz) CASCADE;
DROP FUNCTION IF EXISTS admin_suspend_merchant(uuid) CASCADE;
DROP FUNCTION IF EXISTS admin_suspend_member(uuid) CASCADE;
DROP FUNCTION IF EXISTS unfreeze_card(uuid) CASCADE;
DROP FUNCTION IF EXISTS freeze_card(uuid) CASCADE;
DROP FUNCTION IF EXISTS update_points_and_level(uuid, int, text) CASCADE;
DROP FUNCTION IF EXISTS user_recharge_card(uuid, numeric, pay_method, jsonb, text, text) CASCADE;
DROP FUNCTION IF EXISTS merchant_refund_tx(text, text, numeric, jsonb) CASCADE;
DROP FUNCTION IF EXISTS merchant_charge_by_qr(text, text, numeric, text, jsonb, text) CASCADE;
DROP FUNCTION IF EXISTS cron_rotate_qr_tokens(integer) CASCADE;
DROP FUNCTION IF EXISTS validate_qr_plain(text) CASCADE;
DROP FUNCTION IF EXISTS revoke_card_qr(uuid) CASCADE;
DROP FUNCTION IF EXISTS rotate_card_qr(uuid, integer) CASCADE;
DROP FUNCTION IF EXISTS unbind_member_from_card(uuid, uuid) CASCADE;
DROP FUNCTION IF EXISTS bind_member_to_card(uuid, uuid, bind_role, text) CASCADE;
DROP FUNCTION IF EXISTS create_member_profile(text, text, text, text, text, card_type) CASCADE;
DROP FUNCTION IF EXISTS set_merchant_password(uuid, text) CASCADE;
DROP FUNCTION IF EXISTS set_member_password(uuid, text) CASCADE;
DROP FUNCTION IF EXISTS merchant_login(text, text) CASCADE;
DROP FUNCTION IF EXISTS member_login(text, text) CASCADE;
DROP FUNCTION IF EXISTS get_user_profile() CASCADE;
DROP FUNCTION IF EXISTS check_permission(text) CASCADE;
DROP FUNCTION IF EXISTS is_admin() CASCADE;
DROP FUNCTION IF EXISTS get_user_role() CASCADE;
DROP FUNCTION IF EXISTS compute_level(int) CASCADE;
DROP FUNCTION IF EXISTS compute_discount(int) CASCADE;
DROP FUNCTION IF EXISTS sec.card_lock_key(uuid) CASCADE;
DROP FUNCTION IF EXISTS sec.fixed_search_path() CASCADE;
DROP FUNCTION IF EXISTS cleanup_expired_sessions() CASCADE;
DROP FUNCTION IF EXISTS load_session(text) CASCADE;
DROP FUNCTION IF EXISTS logout_session(text) CASCADE;

-- Helper: create sec schema and functions if not exists
CREATE SCHEMA IF NOT EXISTS sec;

-- Fixed search path function
CREATE OR REPLACE FUNCTION sec.fixed_search_path()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  SET search_path = public, pg_temp;
END;
$$;

-- Card lock key function
CREATE OR REPLACE FUNCTION sec.card_lock_key(card_id uuid)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN ('x' || substr(card_id::text, 1, 15))::bit(60)::bigint;
END;
$$;

-- Compute discount based on points
CREATE OR REPLACE FUNCTION compute_discount(p_points int)
RETURNS numeric(4,3)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_discount numeric(4,3);
BEGIN
  SELECT ml.discount INTO v_discount
  FROM membership_levels ml
  WHERE p_points >= ml.min_points
    AND (ml.max_points IS NULL OR p_points <= ml.max_points)
    AND ml.is_active = true
  ORDER BY ml.level DESC
  LIMIT 1;
  
  RETURN COALESCE(v_discount, 1.000);
END;
$$;

-- Compute level based on points
CREATE OR REPLACE FUNCTION compute_level(p_points int)
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_level int;
BEGIN
  SELECT ml.level INTO v_level
  FROM membership_levels ml
  WHERE p_points >= ml.min_points
    AND (ml.max_points IS NULL OR p_points <= ml.max_points)
    AND ml.is_active = true
  ORDER BY ml.level DESC
  LIMIT 1;
  
  RETURN COALESCE(v_level, 0);
END;
$$;

-- Grant RLS bypass to functions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres;
-- ============================================================================
-- SESSION MANAGEMENT FUNCTIONS (Session 管理函數)
-- ============================================================================

-- 清理過期 session
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_deleted int;
BEGIN
  DELETE FROM public.app_sessions WHERE expires_at < now_utc();
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END;
$$;

COMMENT ON FUNCTION cleanup_expired_sessions IS '清理過期的 session';

-- 驗證並加載 session
CREATE OR REPLACE FUNCTION load_session(p_session_id text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_session public.app_sessions%ROWTYPE;
BEGIN
  IF p_session_id IS NULL THEN
    RETURN false;
  END IF;
  
  -- 查詢 session
  SELECT * INTO v_session
  FROM public.app_sessions
  WHERE session_id = p_session_id
    AND expires_at > now_utc();
  
  IF NOT FOUND THEN
    RETURN false;
  END IF;
  
  -- 設置 session 變數
  PERFORM set_config('app.user_role', v_session.user_role, false);
  PERFORM set_config('app.user_id', v_session.user_id::text, false);
  
  IF v_session.merchant_id IS NOT NULL THEN
    PERFORM set_config('app.merchant_id', v_session.merchant_id::text, false);
  END IF;
  
  IF v_session.member_id IS NOT NULL THEN
    PERFORM set_config('app.member_id', v_session.member_id::text, false);
  END IF;
  
  -- 更新最後訪問時間
  UPDATE public.app_sessions
  SET last_accessed_at = now_utc()
  WHERE session_id = p_session_id;
  
  RETURN true;
END;
$$;

COMMENT ON FUNCTION load_session IS '驗證並加載 session 到當前連接';

-- 登出（刪除 session）
CREATE OR REPLACE FUNCTION logout_session(p_session_id text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  DELETE FROM public.app_sessions WHERE session_id = p_session_id;
  RETURN FOUND;
END;
$$;

COMMENT ON FUNCTION logout_session IS '登出並刪除 session';

-- ============================================================================
-- AUTHENTICATION & AUTHORIZATION FUNCTIONS (認證與授權函數)
-- ============================================================================

-- 取得當前用戶角色
CREATE OR REPLACE FUNCTION get_user_role()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  v_role text;
  v_auth_uid uuid;
BEGIN
  -- 1. 檢查 session 變數（自定義登入）
  BEGIN
    v_role := current_setting('app.user_role', true);
    -- 只有非空且非空字符串時才返回
    IF v_role IS NOT NULL AND v_role != '' THEN
      RETURN v_role;
    END IF;
  EXCEPTION WHEN OTHERS THEN
    -- 繼續檢查 Supabase Auth
  END;
  
  -- 2. 檢查 Supabase Auth
  v_auth_uid := auth.uid();
  
  IF v_auth_uid IS NULL THEN
    RETURN NULL;
  END IF;
  
  -- 3. 優先檢查 admin_users（super_admin 優先級最高）
  SELECT role INTO v_role
  FROM admin_users
  WHERE auth_user_id = v_auth_uid
    AND is_active = true
  LIMIT 1;
  
  IF v_role IS NOT NULL THEN
    RETURN v_role;
  END IF;
  
  -- 4. 檢查 merchant_users
  SELECT 'merchant' INTO v_role
  FROM merchant_users
  WHERE auth_user_id = v_auth_uid
  LIMIT 1;
  
  IF v_role IS NOT NULL THEN
    RETURN v_role;
  END IF;
  
  -- 5. 檢查 member_profiles
  SELECT 'member' INTO v_role
  FROM member_profiles
  WHERE auth_user_id = v_auth_uid
    AND status = 'active'
  LIMIT 1;
  
  RETURN v_role;
END;
$$;

-- 檢查是否為管理員
CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM admin_users
    WHERE auth_user_id = auth.uid() AND is_active = true
  );
$$;

-- 統一的權限檢查函數
CREATE OR REPLACE FUNCTION check_permission(required_role text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_user_role text;
BEGIN
  v_user_role := get_user_role();
  
  IF v_user_role IS NULL THEN
    RAISE EXCEPTION 'NOT_AUTHENTICATED';
  END IF;
  
  -- Super admin 擁有所有權限
  IF v_user_role = 'super_admin' THEN
    RETURN;
  END IF;
  
  -- 其他角色只能執行自己角色的操作
  IF v_user_role = required_role THEN
    RETURN;
  END IF;
  
  RAISE EXCEPTION 'PERMISSION_DENIED: Required %, but user is %',
                  required_role, v_user_role;
END;
$$;

-- 清除 session 變數（用於測試和重新登入）
CREATE OR REPLACE FUNCTION reset_session_variables()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- 重置所有可能的 session 變數（使用空字符串而不是 NULL）
  BEGIN
    PERFORM set_config('app.user_role', '', false);
  EXCEPTION WHEN OTHERS THEN
    -- 忽略錯誤
  END;
  
  BEGIN
    PERFORM set_config('app.user_id', '', false);
  EXCEPTION WHEN OTHERS THEN
    -- 忽略錯誤
  END;
  
  BEGIN
    PERFORM set_config('app.session_id', '', false);
  EXCEPTION WHEN OTHERS THEN
    -- 忽略錯誤
  END;
END;
$$;

COMMENT ON FUNCTION reset_session_variables IS '清除所有 session 變數（用於測試和重新登入）';

-- 取得用戶資料
CREATE OR REPLACE FUNCTION get_user_profile()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
  v_profile jsonb;
  v_role text;
BEGIN
  v_role := get_user_role();
  
  IF v_role IS NULL THEN RETURN NULL; END IF;
  
  IF v_role IN ('admin', 'super_admin') THEN
    SELECT jsonb_build_object(
      'role', role,
      'id', id,
      'name', name,
      'permissions', permissions,
      'is_super_admin', (role = 'super_admin')
    ) INTO v_profile
    FROM admin_users
    WHERE auth_user_id = auth.uid();
    
  ELSIF v_role = 'merchant' THEN
    SELECT jsonb_build_object(
      'role', 'merchant',
      'merchant_id', mu.merchant_id,
      'merchant_code', m.code,
      'merchant_name', m.name,
      'user_role', mu.role
    ) INTO v_profile
    FROM merchant_users mu
    JOIN merchants m ON m.id = mu.merchant_id
    WHERE mu.auth_user_id = auth.uid();
    
  ELSIF v_role = 'member' THEN
    SELECT jsonb_build_object(
      'role', 'member',
      'member_id', id,
      'member_no', member_no,
      'name', name,
      'phone', phone,
      'email', email
    ) INTO v_profile
    FROM member_profiles
    WHERE auth_user_id = auth.uid();
  END IF;
  
  RETURN v_profile;
END;
$$;

-- 會員登入驗證
CREATE OR REPLACE FUNCTION member_login(
  p_identifier text,  -- phone 或 member_no
  p_password text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member member_profiles%ROWTYPE;
  v_session_id text;
  v_expires_at timestamptz;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 查找會員
  SELECT * INTO v_member
  FROM member_profiles
  WHERE (phone = p_identifier OR member_no = p_identifier)
    AND status = 'active'
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 檢查密碼
  IF v_member.password_hash IS NULL THEN
    RAISE EXCEPTION 'PASSWORD_NOT_SET';
  END IF;
  
  IF NOT (v_member.password_hash = extensions.crypt(p_password, v_member.password_hash)) THEN
    INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
    VALUES (NULL, 'LOGIN_FAILED', 'member_profiles', v_member.id,
            jsonb_build_object('identifier', p_identifier), now_utc());
    RAISE EXCEPTION 'INVALID_PASSWORD';
  END IF;
  
  -- 生成 session
  v_session_id := encode(extensions.gen_random_bytes(32), 'base64');
  v_expires_at := now_utc() + interval '24 hours';
  
  -- 存儲 session
  INSERT INTO public.app_sessions(
    session_id, user_role, user_id, member_id, expires_at
  ) VALUES (
    v_session_id,
    'member',
    v_member.id,
    v_member.id,
    v_expires_at
  );
  
  -- 設置 session 變數（用於 get_user_role）
  PERFORM set_config('app.user_role', 'member', false);
  PERFORM set_config('app.user_id', v_member.id::text, false);
  PERFORM set_config('app.session_id', v_session_id, false);
  
  -- 記錄成功登入
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (NULL, 'LOGIN_SUCCESS', 'member_profiles', v_member.id,
          jsonb_build_object('identifier', p_identifier), now_utc());
  
  RETURN jsonb_build_object(
    'success', true,
    'role', 'member',
    'member_id', v_member.id,
    'member_no', v_member.member_no,
    'name', v_member.name,
    'phone', v_member.phone,
    'email', v_member.email,
    'session_id', v_session_id,
    'expires_at', v_expires_at
  );
END;
$$;

-- 商戶登入驗證
CREATE OR REPLACE FUNCTION merchant_login(
  p_merchant_code text,
  p_password text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant merchants%ROWTYPE;
  v_session_id text;
  v_expires_at timestamptz;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 查找商戶
  SELECT * INTO v_merchant
  FROM merchants
  WHERE code = p_merchant_code AND status = 'active'
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  -- 檢查密碼
  IF v_merchant.password_hash IS NULL THEN
    RAISE EXCEPTION 'PASSWORD_NOT_SET';
  END IF;
  
  IF NOT (v_merchant.password_hash = extensions.crypt(p_password, v_merchant.password_hash)) THEN
    INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
    VALUES (NULL, 'LOGIN_FAILED', 'merchants', v_merchant.id,
            jsonb_build_object('code', p_merchant_code), now_utc());
    RAISE EXCEPTION 'INVALID_PASSWORD';
  END IF;
  
  -- 生成 session
  v_session_id := encode(extensions.gen_random_bytes(32), 'base64');
  v_expires_at := now_utc() + interval '24 hours';
  
  -- 存儲 session
  INSERT INTO public.app_sessions(
    session_id, user_role, user_id, merchant_id, expires_at
  ) VALUES (
    v_session_id,
    'merchant',
    v_merchant.id,
    v_merchant.id,
    v_expires_at
  );
  
  -- 設置 session 變數（用於 get_user_role）
  PERFORM set_config('app.user_role', 'merchant', false);
  PERFORM set_config('app.user_id', v_merchant.id::text, false);
  PERFORM set_config('app.session_id', v_session_id, false);
  
  -- 記錄成功登入
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (NULL, 'LOGIN_SUCCESS', 'merchants', v_merchant.id,
          jsonb_build_object('code', p_merchant_code), now_utc());
  
  RETURN jsonb_build_object(
    'success', true,
    'role', 'merchant',
    'merchant_id', v_merchant.id,
    'merchant_code', v_merchant.code,
    'merchant_name', v_merchant.name,
    'session_id', v_session_id,
    'expires_at', v_expires_at
  );
END;
$$;

-- 設定會員密碼
CREATE OR REPLACE FUNCTION set_member_password(
  p_member_id uuid,
  p_password text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  
  IF length(p_password) < 6 THEN
    RAISE EXCEPTION 'PASSWORD_TOO_SHORT';
  END IF;
  
  UPDATE member_profiles
  SET password_hash = extensions.crypt(p_password, extensions.gen_salt('bf')),
      updated_at = now_utc()
  WHERE id = p_member_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'PASSWORD_CHANGED', 'member_profiles', p_member_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;

-- 設定商戶密碼
CREATE OR REPLACE FUNCTION set_merchant_password(
  p_merchant_id uuid,
  p_password text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  IF length(p_password) < 6 THEN
    RAISE EXCEPTION 'PASSWORD_TOO_SHORT';
  END IF;
  
  UPDATE merchants
  SET password_hash = extensions.crypt(p_password, extensions.gen_salt('bf')),
      updated_at = now_utc()
  WHERE id = p_merchant_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'PASSWORD_CHANGED', 'merchants', p_merchant_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;


-- =======================
-- A) MEMBER & BINDINGS
-- =======================

CREATE OR REPLACE FUNCTION create_member_profile(
  p_name               text,
  p_phone              text,
  p_email              text,
  p_password           text DEFAULT NULL,   -- 新增：會員密碼
  p_binding_user_org   text DEFAULT NULL,   -- e.g. 'wechat'
  p_binding_org_id     text DEFAULT NULL,   -- e.g. openid
  p_default_card_type  card_type DEFAULT 'standard'     -- always issues standard; arg reserved
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id  uuid := extensions.gen_random_uuid();
  v_card_id    uuid := extensions.gen_random_uuid();
  v_password_hash text := NULL;
BEGIN
  PERFORM sec.fixed_search_path();

  -- 處理密碼雜湊
  IF p_password IS NOT NULL AND length(p_password) >= 6 THEN
    v_password_hash := extensions.crypt(p_password, extensions.gen_salt('bf'));
  END IF;

  -- 1) Create member
  INSERT INTO member_profiles(id, name, phone, email, password_hash, status, created_at, updated_at)
  VALUES (v_member_id, p_name, p_phone, p_email, v_password_hash, 'active', now_utc(), now_utc());

  -- 2) Auto issue a STANDARD card (1:1; password NULL)
  INSERT INTO member_cards(id, card_no, owner_member_id, card_type, level, discount, points, balance, status, created_at, updated_at, binding_password_hash)
  VALUES (v_card_id,
          gen_card_no('standard'),
          v_member_id,
          'standard',
          0,
          compute_discount(0),
          0,
          0,
          'active',
          now_utc(),
          now_utc(),
          NULL);

  -- 3) Bind owner (explicit binding table, if present)
  INSERT INTO card_bindings(card_id, member_id, role, created_at)
  VALUES (v_card_id, v_member_id, 'owner', now_utc());

  -- 4) Optional external identity binding
  IF p_binding_user_org IS NOT NULL AND p_binding_org_id IS NOT NULL THEN
    BEGIN
      INSERT INTO member_external_identities(member_id, provider, external_id, meta, created_at)
      VALUES (v_member_id, p_binding_user_org, p_binding_org_id, '{}'::jsonb, now_utc());
    EXCEPTION WHEN unique_violation THEN
      RAISE EXCEPTION 'EXTERNAL_ID_ALREADY_BOUND';
    END;
  END IF;

  -- 5) Audit
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CREATE_MEMBER', 'member_profiles', v_member_id,
          jsonb_build_object('name', p_name, 'phone', p_phone, 'email', p_email), now_utc());

  RETURN v_member_id;
END;
$$;

CREATE OR REPLACE FUNCTION bind_member_to_card(
  p_card_id uuid,
  p_member_id uuid,
  p_role bind_role DEFAULT 'member',
  p_binding_password text DEFAULT NULL,
  p_session_id text DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
  v_owner_password_hash text;
  v_owner_count int;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;

  SELECT * INTO v_card FROM member_cards WHERE id = p_card_id;
  IF NOT FOUND OR v_card.status <> 'active' THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND_OR_INACTIVE';
  END IF;

  -- Standard and voucher are non-shareable
  IF v_card.card_type IN ('standard','voucher') AND p_member_id <> v_card.owner_member_id THEN
    RAISE EXCEPTION 'CARD_TYPE_NOT_SHAREABLE';
  END IF;

  -- For corporate: require password if defined
  IF v_card.card_type = 'corporate' THEN
    SELECT COUNT(*) INTO v_owner_count
    FROM card_bindings
    WHERE card_id = v_card.id AND role = 'owner';
    IF v_owner_count = 0 THEN
      RAISE EXCEPTION 'CARD_OWNER_NOT_DEFINED';
    END IF;

    IF v_card.binding_password_hash IS NOT NULL THEN
      IF p_binding_password IS NULL OR NOT (v_card.binding_password_hash = extensions.crypt(p_binding_password, v_card.binding_password_hash)) THEN
        RAISE EXCEPTION 'INVALID_BINDING_PASSWORD';
      END IF;
    END IF;
  END IF;

  -- Prevent duplicate role conflict
  INSERT INTO card_bindings(card_id, member_id, role, created_at)
  VALUES (p_card_id, p_member_id, p_role, now_utc())
  ON CONFLICT (card_id, member_id) DO UPDATE SET role = EXCLUDED.role;

  -- 如果綁定的是企業折扣卡，設置企業折扣到會員的 Standard Card
  IF v_card.card_type = 'corporate' AND v_card.fixed_discount IS NOT NULL THEN
    UPDATE member_cards
    SET corporate_discount = v_card.fixed_discount  -- 設置企業折扣
    WHERE owner_member_id = p_member_id
      AND card_type = 'standard'
      AND status = 'active';
  END IF;

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'BIND_CARD', 'member_cards', p_card_id,
          jsonb_build_object('member_id', p_member_id, 'role', p_role), now_utc());
  RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION unbind_member_from_card(
  p_card_id uuid,
  p_member_id uuid,
  p_session_id text DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_owner_left int;
  v_card member_cards%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;

  -- 獲取卡片信息
  SELECT * INTO v_card FROM member_cards WHERE id = p_card_id;

  DELETE FROM card_bindings
  WHERE card_id = p_card_id AND member_id = p_member_id;

  SELECT COUNT(*) INTO v_owner_left FROM card_bindings WHERE card_id = p_card_id AND role = 'owner';
  IF v_owner_left = 0 THEN
    RAISE EXCEPTION 'CANNOT_REMOVE_LAST_OWNER';
  END IF;

  -- 如果解綁的是企業折扣卡，清除企業折扣
  IF v_card.card_type = 'corporate' THEN
    UPDATE member_cards
    SET corporate_discount = NULL  -- 清除企業折扣
    WHERE owner_member_id = p_member_id
      AND card_type = 'standard'
      AND status = 'active';
  END IF;

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'UNBIND_CARD', 'member_cards', p_card_id, 
          jsonb_build_object('member_id', p_member_id), now_utc());
  RETURN TRUE;
END;
$$;

-- =======================
-- B) QR CODE MANAGEMENT
-- =======================

CREATE OR REPLACE FUNCTION rotate_card_qr(
  p_card_id uuid,
  p_ttl_seconds integer DEFAULT 900,
  p_session_id text DEFAULT NULL
) RETURNS TABLE(qr_plain text, qr_expires_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_plain text := encode(extensions.gen_random_bytes(32),'base64');
  v_hash  text;
  v_expires timestamptz := now_utc() + make_interval(secs => GREATEST(p_ttl_seconds, 60));
  v_user_role text;
  v_has_permission boolean := false;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  -- 獲取當前用戶角色
  v_user_role := get_user_role();
  
  -- 權限檢查：只有 super_admin 和 member 可以生成 QR，merchant 不行
  IF v_user_role = 'super_admin' THEN
    -- Super Admin 可以為任何卡片生成 QR（測試和管理用途）
    v_has_permission := true;
    
  ELSIF v_user_role = 'member' THEN
    -- Member 只能為自己擁有或綁定的卡片生成 QR
    SELECT EXISTS (
      -- 檢查是否為卡片擁有者
      SELECT 1 FROM member_cards mc
      JOIN member_profiles mp ON mp.id = mc.owner_member_id
      WHERE mc.id = p_card_id
        AND (
          -- Supabase Auth 用戶
          (mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text)
          OR
          -- 自定義登入用戶（通過 session 變數）
          (mp.id::text = current_setting('app.user_id', true))
        )
      
      UNION
      
      -- 檢查是否已綁定此卡片（企業卡共享）
      SELECT 1 FROM card_bindings cb
      JOIN member_profiles mp ON mp.id = cb.member_id
      WHERE cb.card_id = p_card_id
        AND cb.status = 'active'
        AND (
          (mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text)
          OR
          (mp.id::text = current_setting('app.user_id', true))
        )
    ) INTO v_has_permission;
    
  ELSIF v_user_role = 'merchant' THEN
    -- Merchant 不能生成 QR 碼，只能掃碼收款
    RAISE EXCEPTION 'PERMISSION_DENIED: 商戶不能生成 QR 碼';
    
  ELSE
    -- 未登入或其他角色
    RAISE EXCEPTION 'PERMISSION_DENIED: 需要登入才能生成 QR 碼';
  END IF;
  
  -- 拒絕無權限的請求
  IF NOT v_has_permission THEN
    RAISE EXCEPTION 'PERMISSION_DENIED: 您沒有權限為此卡片生成 QR 碼';
  END IF;
  
  v_hash := extensions.crypt(v_plain, extensions.gen_salt('bf'));

  -- Upsert current QR state
  INSERT INTO card_qr_state(card_id, token_hash, updated_at, expires_at)
  VALUES (p_card_id, v_hash, now_utc(), v_expires)
  ON CONFLICT (card_id) DO UPDATE
    SET token_hash = EXCLUDED.token_hash,
        updated_at = EXCLUDED.updated_at,
        expires_at = EXCLUDED.expires_at;

  -- Append history
  INSERT INTO card_qr_history(card_id, token_hash, issued_at, expires_at)
  VALUES (p_card_id, v_hash, now_utc(), v_expires);

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'QR_ROTATE', 'member_cards', p_card_id, 
          jsonb_build_object('ttl', p_ttl_seconds), now_utc());
  RETURN QUERY SELECT v_plain, v_expires;
END;
$$;

CREATE OR REPLACE FUNCTION revoke_card_qr(
  p_card_id uuid,
  p_session_id text DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_user_role text;
  v_has_permission boolean := false;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  -- 獲取當前用戶角色
  v_user_role := get_user_role();
  
  -- 權限檢查：與 rotate_card_qr 相同邏輯
  IF v_user_role = 'super_admin' THEN
    v_has_permission := true;
  ELSIF v_user_role = 'member' THEN
    SELECT EXISTS (
      SELECT 1 FROM member_cards mc
      JOIN member_profiles mp ON mp.id = mc.owner_member_id
      WHERE mc.id = p_card_id
        AND (
          (mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text)
          OR
          (mp.id::text = current_setting('app.user_id', true))
        )
      UNION
      SELECT 1 FROM card_bindings cb
      JOIN member_profiles mp ON mp.id = cb.member_id
      WHERE cb.card_id = p_card_id
        AND cb.status = 'active'
        AND (
          (mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text)
          OR
          (mp.id::text = current_setting('app.user_id', true))
        )
    ) INTO v_has_permission;
  ELSIF v_user_role = 'merchant' THEN
    RAISE EXCEPTION 'PERMISSION_DENIED: 商戶不能撤銷 QR 碼';
  ELSE
    RAISE EXCEPTION 'PERMISSION_DENIED: 需要登入才能撤銷 QR 碼';
  END IF;
  
  IF NOT v_has_permission THEN
    RAISE EXCEPTION 'PERMISSION_DENIED: 您沒有權限撤銷此卡片的 QR 碼';
  END IF;
  
  UPDATE card_qr_state SET expires_at = now_utc() WHERE card_id = p_card_id;
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'QR_REVOKE', 'member_cards', p_card_id, '{}'::jsonb, now_utc());
  RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION validate_qr_plain(
  p_qr_plain text
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  IF p_qr_plain IS NULL OR length(p_qr_plain) < 16 THEN
    RAISE EXCEPTION 'INVALID_QR';
  END IF;

  SELECT s.card_id INTO v_card_id
  FROM card_qr_state s
  WHERE s.expires_at > now_utc()
    AND s.token_hash = extensions.crypt(p_qr_plain, s.token_hash)
  LIMIT 1;

  IF v_card_id IS NULL THEN
    RAISE EXCEPTION 'QR_EXPIRED_OR_INVALID';
  END IF;

  RETURN v_card_id;
END;
$$;

CREATE OR REPLACE FUNCTION cron_rotate_qr_tokens(
  p_ttl_seconds integer DEFAULT 300
) RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_cnt int := 0;
  r RECORD;
  v_plain text;
  v_hash  text;
  v_expires timestamptz := now_utc() + make_interval(secs => GREATEST(p_ttl_seconds, 60));
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  FOR r IN
    SELECT id FROM member_cards WHERE status='active' AND card_type = 'corporate'
  LOOP
    v_plain := encode(extensions.gen_random_bytes(32),'base64');
    v_hash := extensions.crypt(v_plain, extensions.gen_salt('bf'));
    INSERT INTO card_qr_state(card_id, token_hash, updated_at, expires_at)
    VALUES (r.id, v_hash, now_utc(), v_expires)
    ON CONFLICT (card_id) DO UPDATE
      SET token_hash = EXCLUDED.token_hash,
          updated_at = EXCLUDED.updated_at,
          expires_at = EXCLUDED.expires_at;
    INSERT INTO card_qr_history(card_id, token_hash, issued_at, expires_at)
    VALUES (r.id, v_hash, now_utc(), v_expires);
    v_cnt := v_cnt + 1;
  END LOOP;
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'QR_CRON_ROTATE', 'system', NULL, 
          jsonb_build_object('affected', v_cnt), now_utc());
  RETURN v_cnt;
END;
$$;

-- =======================
-- C) PAYMENTS / REFUNDS / RECHARGE
-- =======================

CREATE OR REPLACE FUNCTION merchant_charge_by_qr(
  p_merchant_code text,
  p_qr_plain text,
  p_raw_amount numeric,
  p_idempotency_key text DEFAULT NULL,
  p_tag jsonb DEFAULT '{}'::jsonb,
  p_external_order_id text DEFAULT NULL,
  p_session_id text DEFAULT NULL
) RETURNS TABLE (tx_id uuid, tx_no text, card_id uuid, final_amount numeric, discount numeric)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merch merchants%ROWTYPE;
  v_user_role text;
  v_current_merchant_id text;
  v_is_authorized boolean := false;
  v_card member_cards%ROWTYPE;
  v_disc numeric(4,3) := 1.000;
  v_final numeric(12,2);
  v_tx_id uuid := extensions.gen_random_uuid();
  v_tx_no text;
  v_ref_exists uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;

  -- 驗證金額
  IF p_raw_amount IS NULL OR p_raw_amount <= 0 THEN
    RAISE EXCEPTION 'INVALID_PRICE';
  END IF;

  -- 獲取商戶
  SELECT * INTO v_merch FROM merchants WHERE code=p_merchant_code AND status='active';
  IF NOT FOUND THEN RAISE EXCEPTION 'MERCHANT_NOT_FOUND_OR_INACTIVE'; END IF;

  -- 權限檢查
  v_user_role := get_user_role();
  
  IF v_user_role = 'super_admin' THEN
    -- Super Admin 可以代替任何商戶執行支付
    v_is_authorized := true;
    
  ELSIF v_user_role = 'merchant' THEN
    -- Merchant 只能執行自己的支付
    BEGIN
      v_current_merchant_id := current_setting('app.merchant_id', true);
    EXCEPTION WHEN OTHERS THEN
      v_current_merchant_id := NULL;
    END;
    
    IF v_current_merchant_id = v_merch.id::text THEN
      v_is_authorized := true;
    END IF;
  END IF;
  
  IF NOT v_is_authorized THEN
    RAISE EXCEPTION 'NOT_AUTHORIZED_FOR_THIS_MERCHANT';
  END IF;

  -- Validate QR -> card_id
  SELECT * INTO v_card FROM member_cards WHERE id = validate_qr_plain(p_qr_plain) FOR UPDATE;
  IF v_card.status <> 'active' THEN RAISE EXCEPTION 'CARD_NOT_ACTIVE'; END IF;
  IF v_card.expires_at IS NOT NULL AND v_card.expires_at < now_utc() THEN RAISE EXCEPTION 'CARD_EXPIRED'; END IF;

  -- Idempotency by key
  IF p_idempotency_key IS NOT NULL THEN
    BEGIN
      INSERT INTO idempotency_registry(idempotency_key, tx_id, created_at) VALUES (p_idempotency_key, v_tx_id, now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount, t.discount_applied
        FROM idempotency_registry ir
        JOIN transactions t ON t.id = ir.tx_id
        WHERE ir.idempotency_key = p_idempotency_key AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  -- Optional external order mapping
  IF p_external_order_id IS NOT NULL THEN
    BEGIN
      INSERT INTO merchant_order_registry(merchant_id, external_order_id, tx_id, created_at)
      VALUES (v_merch.id, p_external_order_id, v_tx_id, now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount, t.discount_applied
        FROM merchant_order_registry mo
        JOIN transactions t ON t.id = mo.tx_id
        WHERE mo.merchant_id=v_merch.id AND mo.external_order_id=p_external_order_id AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  -- Discount rule by card type
  IF v_card.card_type = 'standard' THEN
    -- 取積分等級折扣和企業折扣中的最優值
    v_disc := LEAST(
      v_card.discount,  -- 積分等級折扣
      COALESCE(v_card.corporate_discount, 1.000)  -- 企業折扣（如果有）
    );
  ELSIF v_card.card_type = 'corporate' THEN
    RAISE EXCEPTION 'CORPORATE_CARD_CANNOT_PAY';  -- 企業卡不能直接支付
  ELSE
    RAISE EXCEPTION 'UNSUPPORTED_CARD_TYPE_FOR_PAYMENT';
  END IF;

  v_final := round(p_raw_amount * v_disc, 2);
  IF v_card.balance < v_final THEN RAISE EXCEPTION 'INSUFFICIENT_BALANCE'; END IF;

  -- Create tx number registry
  v_tx_no := gen_tx_no('payment');
  INSERT INTO tx_registry(tx_no, tx_id, created_at) VALUES (v_tx_no, v_tx_id, now_utc()) ON CONFLICT DO NOTHING;

  -- Insert transaction
  INSERT INTO transactions(id, tx_no, card_id, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned, status, tag, payment_method, created_at)
  VALUES (v_tx_id, v_tx_no, v_card.id, v_merch.id, 'payment',
    p_raw_amount, v_disc, v_final,
    CASE WHEN v_card.card_type = 'standard' THEN floor(p_raw_amount)::int ELSE 0 END,
    'processing', COALESCE(p_tag,'{}'::jsonb), 'balance', now_utc());

  -- Update balances / points
  UPDATE member_cards
  SET balance = balance - v_final,
      points  = CASE WHEN card_type = 'standard' THEN points + floor(p_raw_amount)::int ELSE points END,
      level   = CASE WHEN card_type = 'standard'
                      THEN compute_level(points + floor(p_raw_amount)::int)
                      ELSE level END,
      discount = CASE WHEN member_cards.card_type = 'standard'
                      THEN compute_discount(member_cards.points + floor(p_raw_amount)::int)
                      ELSE member_cards.discount END,
      updated_at = now_utc()
  WHERE id = v_card.id;

  -- Point ledger
  IF v_card.card_type = 'standard' THEN
    INSERT INTO point_ledger(id, card_id, tx_id, change, balance_before, balance_after, reason, created_at)
    VALUES (extensions.gen_random_uuid(), v_card.id, v_tx_id, floor(p_raw_amount)::int, v_card.points,
            (SELECT points FROM member_cards WHERE id=v_card.id), 'payment_earn', now_utc());
  END IF;

  UPDATE transactions SET status='completed' WHERE id = v_tx_id;

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'PAYMENT', 'transactions', v_tx_id, 
          jsonb_build_object('merchant', v_merch.code, 'final', v_final), now_utc());

  RETURN QUERY SELECT v_tx_id, v_tx_no, v_card.id, v_final, v_disc;
END;
$$;

CREATE OR REPLACE FUNCTION merchant_refund_tx(
  p_merchant_code text,
  p_original_tx_no text,
  p_refund_amount numeric,
  p_tag jsonb DEFAULT '{}'::jsonb,
  p_session_id text DEFAULT NULL
) RETURNS TABLE (refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merch merchants%ROWTYPE;
  v_user_role text;
  v_current_merchant_id text;
  v_is_authorized boolean := false;
  v_orig transactions%ROWTYPE;
  v_left numeric(12,2);
  v_ref_tx_id uuid := extensions.gen_random_uuid();
  v_ref_tx_no text;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  -- 驗證退款金額
  IF p_refund_amount IS NULL OR p_refund_amount <= 0 THEN
    RAISE EXCEPTION 'INVALID_REFUND_AMOUNT';
  END IF;

  -- 獲取商戶
  SELECT * INTO v_merch FROM merchants WHERE code=p_merchant_code AND status='active';
  IF NOT FOUND THEN RAISE EXCEPTION 'MERCHANT_NOT_FOUND_OR_INACTIVE'; END IF;

  -- 權限檢查
  v_user_role := get_user_role();
  
  IF v_user_role = 'super_admin' THEN
    -- Super Admin 可以執行所有商戶的退款
    v_is_authorized := true;
    
  ELSIF v_user_role = 'merchant' THEN
    -- Merchant 只能退款自己的交易
    BEGIN
      v_current_merchant_id := current_setting('app.merchant_id', true);
    EXCEPTION WHEN OTHERS THEN
      v_current_merchant_id := NULL;
    END;
    
    -- 驗證是否為同一商戶
    IF v_current_merchant_id = v_merch.id::text THEN
      v_is_authorized := true;
    END IF;
  END IF;
  
  IF NOT v_is_authorized THEN
    RAISE EXCEPTION 'NOT_AUTHORIZED_FOR_THIS_MERCHANT';
  END IF;

  SELECT * INTO v_orig FROM transactions WHERE tx_no=p_original_tx_no AND merchant_id=v_merch.id;
  IF NOT FOUND THEN RAISE EXCEPTION 'ORIGINAL_TX_NOT_FOUND'; END IF;
  IF v_orig.tx_type <> 'payment' OR v_orig.status NOT IN ('completed','refunded') THEN
    RAISE EXCEPTION 'ONLY_COMPLETED_PAYMENT_REFUNDABLE';
  END IF;

  SELECT v_orig.final_amount - COALESCE((
    SELECT SUM(final_amount) FROM transactions
    WHERE tx_type='refund' AND card_id=v_orig.card_id AND reason=v_orig.tx_no AND status IN ('processing','completed')
  ), 0)
  INTO v_left;
  IF v_left IS NULL THEN v_left := v_orig.final_amount; END IF;
  IF p_refund_amount > v_left THEN RAISE EXCEPTION 'REFUND_EXCEEDS_REMAINING'; END IF;

  v_ref_tx_no := gen_tx_no('refund');
  INSERT INTO tx_registry(tx_no, tx_id, created_at) VALUES (v_ref_tx_no, v_ref_tx_id, now_utc()) ON CONFLICT DO NOTHING;

  INSERT INTO transactions(id, tx_no, card_id, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned, status, tag, reason, payment_method, created_at)
  VALUES (v_ref_tx_id, v_ref_tx_no, v_orig.card_id, v_merch.id, 'refund',
    p_refund_amount, 1.000, p_refund_amount, 0, 'processing', COALESCE(p_tag,'{}'::jsonb), v_orig.tx_no, v_orig.payment_method, now_utc());

  UPDATE member_cards SET balance = balance + p_refund_amount, updated_at = now_utc() WHERE id = v_orig.card_id;

  UPDATE transactions SET status='completed' WHERE id = v_ref_tx_id;

  IF p_refund_amount >= v_left THEN
    UPDATE transactions SET status='refunded' WHERE id = v_orig.id;
  END IF;

  -- 記錄審計日誌
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (
    CASE
      WHEN auth.uid() IS NOT NULL THEN auth.uid()
      ELSE NULL
    END,
    'REFUND', 'transactions', v_ref_tx_id,
    jsonb_build_object('merchant', v_merch.code, 'amount', p_refund_amount),
    now_utc()
  );

  RETURN QUERY SELECT v_ref_tx_id, v_ref_tx_no, p_refund_amount;
END;
$$;

CREATE OR REPLACE FUNCTION user_recharge_card(
  p_card_id uuid,
  p_amount numeric,
  p_payment_method pay_method DEFAULT 'wechat',
  p_tag jsonb DEFAULT '{}'::jsonb,
  p_idempotency_key text DEFAULT NULL,
  p_external_order_id text DEFAULT NULL,
  p_session_id text DEFAULT NULL
) RETURNS TABLE (tx_id uuid, tx_no text, card_id uuid, amount numeric)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
  v_tx_id uuid := extensions.gen_random_uuid();
  v_tx_no text;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_RECHARGE_AMOUNT'; END IF;

  SELECT * INTO v_card FROM member_cards WHERE id=p_card_id FOR UPDATE;
  IF NOT FOUND OR v_card.status <> 'active' THEN RAISE EXCEPTION 'CARD_NOT_FOUND_OR_INACTIVE'; END IF;
  -- 只允許 Standard Card 充值（企業卡和優惠券卡不能充值）
  IF v_card.card_type NOT IN ('standard') THEN
    RAISE EXCEPTION 'UNSUPPORTED_CARD_TYPE_FOR_RECHARGE';
  END IF;

  -- Idempotency
  IF p_idempotency_key IS NOT NULL THEN
    BEGIN
      INSERT INTO idempotency_registry(idempotency_key, tx_id, created_at) VALUES (p_idempotency_key, v_tx_id, now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount
        FROM idempotency_registry ir
        JOIN transactions t ON t.id = ir.tx_id
        WHERE ir.idempotency_key = p_idempotency_key AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  -- External order optional map
  IF p_external_order_id IS NOT NULL THEN
    BEGIN
      INSERT INTO merchant_order_registry(merchant_id, external_order_id, tx_id, created_at)
      VALUES (NULL, p_external_order_id, v_tx_id, now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount
        FROM merchant_order_registry mo
        JOIN transactions t ON t.id = mo.tx_id
        WHERE mo.merchant_id IS NULL AND mo.external_order_id = p_external_order_id AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  v_tx_no := gen_tx_no('recharge');
  INSERT INTO tx_registry(tx_no, tx_id, created_at) VALUES (v_tx_no, v_tx_id, now_utc()) ON CONFLICT DO NOTHING;

  INSERT INTO transactions(id, tx_no, card_id, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned, status, tag, reason, payment_method, created_at)
  VALUES (v_tx_id, v_tx_no, v_card.id, NULL, 'recharge',
    p_amount, 1.000, p_amount, 0, 'processing', COALESCE(p_tag,'{}'::jsonb), 'recharge', p_payment_method, now_utc());

  UPDATE member_cards SET balance = balance + p_amount, updated_at = now_utc() WHERE id = v_card.id;

  UPDATE transactions SET status='completed' WHERE id = v_tx_id;

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'RECHARGE', 'transactions', v_tx_id, 
          jsonb_build_object('amount', p_amount, 'method', p_payment_method), now_utc());

  RETURN QUERY SELECT v_tx_id, v_tx_no, v_card.id, p_amount;
END;
$$;

-- =======================
-- D) POINTS & LEVELS
-- =======================

CREATE OR REPLACE FUNCTION update_points_and_level(
  p_card_id uuid,
  p_delta_points int,
  p_reason text DEFAULT 'manual_adjust'
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
  v_new_points int;
  v_new_level int;
  v_new_disc numeric(4,3);
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 只有手動調整時需要管理員權限
  IF p_reason = 'manual_adjust' THEN
    PERFORM check_permission('super_admin');
  END IF;
  
  SELECT * INTO v_card FROM member_cards WHERE id=p_card_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'CARD_NOT_FOUND_OR_INACTIVE'; END IF;
  IF v_card.card_type NOT IN ('standard') THEN
    RAISE EXCEPTION 'UNSUPPORTED_CARD_TYPE_FOR_POINTS';
  END IF;

  v_new_points := GREATEST(0, v_card.points + p_delta_points);
  v_new_level := compute_level(v_new_points);
  v_new_disc := compute_discount(v_new_points);

  UPDATE member_cards
  SET points = v_new_points,
      level = v_new_level,
      discount = v_new_disc,
      updated_at = now_utc()
  WHERE id = v_card.id;

  INSERT INTO point_ledger(id, card_id, tx_id, change, balance_before, balance_after, reason, created_at)
  VALUES (extensions.gen_random_uuid(), v_card.id, NULL, p_delta_points, v_card.points, v_new_points, p_reason, now_utc());

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'POINTS_ADJUST', 'member_cards', v_card.id, 
          jsonb_build_object('delta', p_delta_points, 'reason', p_reason), now_utc());
  RETURN TRUE;
END;
$$;

-- =======================
-- E) ADMIN & RISK
-- =======================

CREATE OR REPLACE FUNCTION freeze_card(
  p_card_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  UPDATE member_cards SET status='inactive', updated_at=now_utc() WHERE id=p_card_id;
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CARD_FREEZE', 'member_cards', p_card_id, '{}'::jsonb, now_utc());
  RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION unfreeze_card(
  p_card_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  UPDATE member_cards SET status='active', updated_at=now_utc() WHERE id=p_card_id;
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CARD_UNFREEZE', 'member_cards', p_card_id, '{}'::jsonb, now_utc());
  RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION admin_suspend_member(
  p_member_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  UPDATE member_profiles SET status='suspended', updated_at=now_utc() WHERE id=p_member_id;
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'MEMBER_SUSPEND', 'member_profiles', p_member_id, '{}'::jsonb, now_utc());
  RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION admin_suspend_merchant(
  p_merchant_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  UPDATE merchants SET status='inactive', updated_at=now_utc() WHERE id=p_merchant_id;
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'MERCHANT_SUSPEND', 'merchants', p_merchant_id, '{}'::jsonb, now_utc());
  RETURN TRUE;
END;
$$;

-- =======================
-- F) SETTLEMENTS & QUERIES
-- =======================

CREATE OR REPLACE FUNCTION generate_settlement(
  p_merchant_id uuid,
  p_mode settlement_mode,
  p_period_start timestamptz,
  p_period_end   timestamptz
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_id uuid := extensions.gen_random_uuid();
  v_total numeric(12,2);
  v_count bigint;
BEGIN
  PERFORM sec.fixed_search_path();

  SELECT COALESCE(SUM(CASE WHEN tx_type='payment' THEN final_amount ELSE -final_amount END),0),
         COUNT(*)
  INTO v_total, v_count
  FROM transactions
  WHERE merchant_id=p_merchant_id
    AND created_at >= p_period_start AND created_at < p_period_end
    AND status IN ('completed','refunded');

  INSERT INTO settlements(id, merchant_id, period_start, period_end, mode, total_amount, total_tx_count, status, created_at)
  VALUES (v_id, p_merchant_id, p_period_start, p_period_end, p_mode, v_total, v_count, 'pending', now_utc());

  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'SETTLEMENT_GENERATE', 'settlements', v_id,
          jsonb_build_object('merchant_id', p_merchant_id, 'total', v_total, 'count', v_count), now_utc());

  RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION list_settlements(
  p_merchant_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_session_id text DEFAULT NULL
) RETURNS TABLE(id uuid, period_start timestamptz, period_end timestamptz, mode settlement_mode, total_amount numeric, total_tx_count bigint, status settlement_status, created_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  RETURN QUERY
  SELECT s.id, s.period_start, s.period_end, s.mode, s.total_amount, s.total_tx_count, s.status, s.created_at
  FROM settlements s
  WHERE s.merchant_id = p_merchant_id
  ORDER BY s.created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

CREATE OR REPLACE FUNCTION get_member_transactions(
  p_member_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_start_date timestamptz DEFAULT NULL,
  p_end_date   timestamptz DEFAULT NULL,
  p_session_id text DEFAULT NULL
) RETURNS TABLE(id uuid, tx_no text, tx_type tx_type, card_id uuid, merchant_id uuid, final_amount numeric, status tx_status, created_at timestamptz, total_count bigint)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_where text := ' WHERE 1=1 ';
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  RETURN QUERY
  WITH cte AS (
    SELECT t.* FROM transactions t
    JOIN member_cards c ON c.id = t.card_id
    WHERE c.owner_member_id = p_member_id
      AND (p_start_date IS NULL OR t.created_at >= p_start_date)
      AND (p_end_date   IS NULL OR t.created_at <  p_end_date)
  )
  SELECT cte.id, cte.tx_no, cte.tx_type, cte.card_id, cte.merchant_id, cte.final_amount, cte.status, cte.created_at,
         COUNT(*) OVER() AS total_count
  FROM cte
  ORDER BY created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

CREATE OR REPLACE FUNCTION get_merchant_transactions(
  p_merchant_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_start_date timestamptz DEFAULT NULL,
  p_end_date   timestamptz DEFAULT NULL,
  p_session_id text DEFAULT NULL
) RETURNS TABLE(id uuid, tx_no text, tx_type tx_type, card_id uuid, final_amount numeric, status tx_status, created_at timestamptz, total_count bigint)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 加載 session
  IF p_session_id IS NOT NULL THEN
    PERFORM load_session(p_session_id);
  END IF;
  
  RETURN QUERY
  WITH cte AS (
    SELECT t.* FROM transactions t
    WHERE t.merchant_id = p_merchant_id
      AND (p_start_date IS NULL OR t.created_at >= p_start_date)
      AND (p_end_date   IS NULL OR t.created_at <  p_end_date)
  )
  SELECT cte.id, cte.tx_no, cte.tx_type, cte.card_id, cte.final_amount, cte.status, cte.created_at,
         COUNT(*) OVER() AS total_count
  FROM cte
  ORDER BY created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

CREATE OR REPLACE FUNCTION get_transaction_detail(
  p_tx_no text
) RETURNS transactions
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_tx transactions%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  SELECT * INTO v_tx FROM transactions WHERE tx_no = p_tx_no;
  IF NOT FOUND THEN RAISE EXCEPTION 'TX_NOT_FOUND'; END IF;
  RETURN v_tx;
END;
$$;

-- =======================
-- G) HELPER FUNCTIONS FOR CLI
-- =======================

-- Get member by auth user
CREATE OR REPLACE FUNCTION get_member_by_auth_user()
RETURNS member_profiles
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member member_profiles%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT * INTO v_member
  FROM member_profiles
  WHERE binding_user_org = 'supabase'
    AND binding_org_id = auth.uid()::text;
    
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  RETURN v_member;
END;
$$;

-- Get member cards
CREATE OR REPLACE FUNCTION get_member_cards(p_member_id uuid DEFAULT NULL)
RETURNS TABLE(
  id uuid,
  card_no text,
  card_type card_type,
  name text,
  balance numeric(12,2),
  points int,
  level int,
  discount numeric(4,3),
  status card_status,
  expires_at timestamptz,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- If no member_id provided, get from auth user
  IF p_member_id IS NULL THEN
    SELECT mp.id INTO v_member_id
    FROM member_profiles mp
    WHERE mp.binding_user_org = 'supabase'
      AND mp.binding_org_id = auth.uid()::text;
      
    IF v_member_id IS NULL THEN
      RAISE EXCEPTION 'MEMBER_NOT_FOUND';
    END IF;
  ELSE
    v_member_id := p_member_id;
  END IF;
  
  RETURN QUERY
  SELECT mc.id, mc.card_no, mc.card_type, mc.name, mc.balance,
         mc.points, mc.level, mc.discount, mc.status, mc.expires_at, mc.created_at
  FROM member_cards mc
  WHERE mc.owner_member_id = v_member_id
     OR mc.id IN (
       SELECT cb.card_id
       FROM card_bindings cb
       WHERE cb.member_id = v_member_id
     )
  ORDER BY mc.created_at DESC;
END;
$$;


-- Get merchant by auth user
CREATE OR REPLACE FUNCTION get_merchant_by_auth_user()
RETURNS merchants
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant merchants%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT m.* INTO v_merchant
  FROM merchants m
  JOIN merchant_users mu ON mu.merchant_id = m.id
  WHERE mu.auth_user_id = auth.uid()
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  RETURN v_merchant;
END;
$$;

-- Simple connection test function
CREATE OR REPLACE FUNCTION test_connection()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_result jsonb;
  v_member_count int;
  v_card_count int;
  v_merchant_count int;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT COUNT(*) INTO v_member_count FROM member_profiles;
  SELECT COUNT(*) INTO v_card_count FROM member_cards;
  SELECT COUNT(*) INTO v_merchant_count FROM merchants;
  
  v_result := jsonb_build_object(
    'status', 'success',
    'timestamp', now_utc(),
    'stats', jsonb_build_object(
      'members', v_member_count,
      'cards', v_card_count,
      'merchants', v_merchant_count
    )
  );
  
  RETURN v_result;
END;
$$;

-- ============================================================================
-- END OF COMMERCIAL RPC FILE
-- ============================================================================
-- ADDITIONAL ADMIN FUNCTIONS (管理員專用函數)
-- ============================================================================

-- 創建商戶
CREATE OR REPLACE FUNCTION create_merchant(
  p_code text,
  p_name text,
  p_contact text DEFAULT NULL,
  p_password text DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant_id uuid := extensions.gen_random_uuid();
  v_password_hash text := NULL;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 處理密碼雜湊
  IF p_password IS NOT NULL AND length(p_password) >= 6 THEN
    v_password_hash := extensions.crypt(p_password, extensions.gen_salt('bf'));
  END IF;
  
  -- 創建商戶
  INSERT INTO merchants(id, code, name, contact, password_hash, status, created_at, updated_at)
  VALUES (v_merchant_id, p_code, p_name, p_contact, v_password_hash, 'active', now_utc(), now_utc());
  
  -- 記錄審計日誌
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CREATE_MERCHANT', 'merchants', v_merchant_id,
          jsonb_build_object('code', p_code, 'name', p_name), now_utc());
  
  RETURN v_merchant_id;
END;
$$;

COMMENT ON FUNCTION create_merchant IS '創建商戶（需要 admin 權限）';

-- 創建企業卡
CREATE OR REPLACE FUNCTION create_corporate_card(
  p_owner_member_id uuid,
  p_name text DEFAULT NULL,
  p_initial_balance numeric(12,2) DEFAULT 0,
  p_fixed_discount numeric(4,3) DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card_id uuid := extensions.gen_random_uuid();
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 驗證會員存在
  IF NOT EXISTS (SELECT 1 FROM member_profiles WHERE id = p_owner_member_id) THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 創建企業卡
  INSERT INTO member_cards(
    id, card_no, card_type, owner_member_id, name,
    balance, points, level, discount, fixed_discount,
    status, created_at, updated_at
  )
  VALUES (
    v_card_id,
    gen_card_no('corporate'),
    'corporate',
    p_owner_member_id,
    p_name,
    p_initial_balance,
    0,
    0,
    COALESCE(p_fixed_discount, 1.000),
    p_fixed_discount,
    'active',
    now_utc(),
    now_utc()
  );
  
  -- 綁定擁有者
  INSERT INTO card_bindings(card_id, member_id, role, created_at)
  VALUES (v_card_id, p_owner_member_id, 'owner', now_utc());
  
  -- 記錄審計日誌
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CREATE_CORPORATE_CARD', 'member_cards', v_card_id,
          jsonb_build_object('owner_member_id', p_owner_member_id, 'name', p_name), now_utc());
  
  RETURN v_card_id;
END;
$$;

COMMENT ON FUNCTION create_corporate_card IS '創建企業卡（需要 admin 權限）';

-- 注意：create_prepaid_card 已移除，所有功能合併到 Standard Card
-- Standard Card 現在支持充值功能

-- 設定卡片綁定密碼
CREATE OR REPLACE FUNCTION set_card_binding_password(
  p_card_id uuid,
  p_password text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 獲取卡片信息
  SELECT * INTO v_card FROM member_cards WHERE id = p_card_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND';
  END IF;
  
  -- 只有 corporate 卡可以設定綁定密碼
  IF v_card.card_type NOT IN ('corporate') THEN
    RAISE EXCEPTION 'CARD_TYPE_NOT_SUPPORT_BINDING_PASSWORD';
  END IF;
  
  -- 密碼長度檢查
  IF length(p_password) < 6 THEN
    RAISE EXCEPTION 'PASSWORD_TOO_SHORT';
  END IF;
  
  -- 更新綁定密碼
  UPDATE member_cards
  SET binding_password_hash = extensions.crypt(p_password, extensions.gen_salt('bf')),
      updated_at = now_utc()
  WHERE id = p_card_id;
  
  -- 記錄審計日誌
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'SET_BINDING_PASSWORD', 'member_cards', p_card_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION set_card_binding_password IS '設定卡片綁定密碼（需要 admin 權限）';

-- 恢復會員（取消暫停）
CREATE OR REPLACE FUNCTION admin_activate_member(
  p_member_id uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  UPDATE member_profiles SET status='active', updated_at=now_utc() WHERE id=p_member_id;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'MEMBER_ACTIVATE', 'member_profiles', p_member_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION admin_activate_member IS '恢復會員（需要 admin 權限）';

-- 恢復商戶（取消暫停）
CREATE OR REPLACE FUNCTION admin_activate_merchant(
  p_merchant_id uuid
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  UPDATE merchants SET status='active', updated_at=now_utc() WHERE id=p_merchant_id;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'MERCHANT_ACTIVATE', 'merchants', p_merchant_id, '{}'::jsonb, now_utc());
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION admin_activate_merchant IS '恢復商戶（需要 admin 權限）';

-- 創建優惠券卡
CREATE OR REPLACE FUNCTION create_voucher_card(
  p_owner_member_id uuid,
  p_name text DEFAULT NULL,
  p_initial_balance numeric(12,2) DEFAULT 0,
  p_expires_at timestamptz DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card_id uuid := extensions.gen_random_uuid();
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 驗證會員存在
  IF NOT EXISTS (SELECT 1 FROM member_profiles WHERE id = p_owner_member_id) THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 創建優惠券卡
  INSERT INTO member_cards(
    id, card_no, card_type, owner_member_id, name,
    balance, points, level, discount,
    status, expires_at, created_at, updated_at
  )
  VALUES (
    v_card_id,
    gen_card_no('voucher'),
    'voucher',
    p_owner_member_id,
    p_name,
    p_initial_balance,
    0,
    0,
    1.000,
    'active',
    p_expires_at,
    now_utc(),
    now_utc()
  );
  
  -- 綁定擁有者
  INSERT INTO card_bindings(card_id, member_id, role, created_at)
  VALUES (v_card_id, p_owner_member_id, 'owner', now_utc());
  
  -- 記錄審計日誌
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'CREATE_VOUCHER_CARD', 'member_cards', v_card_id,
          jsonb_build_object('owner_member_id', p_owner_member_id, 'name', p_name), now_utc());
  
  RETURN v_card_id;
END;
$$;

COMMENT ON FUNCTION create_voucher_card IS '創建優惠券卡（需要 admin 權限）';

-- 獲取商戶詳情
CREATE OR REPLACE FUNCTION get_merchant_detail(
  p_merchant_id uuid
)
RETURNS merchants
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant merchants%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT * INTO v_merchant FROM merchants WHERE id = p_merchant_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  RETURN v_merchant;
END;
$$;

COMMENT ON FUNCTION get_merchant_detail IS '獲取商戶詳情';

-- 獲取卡片詳情
CREATE OR REPLACE FUNCTION get_card_detail(
  p_card_id uuid
)
RETURNS member_cards
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT * INTO v_card FROM member_cards WHERE id = p_card_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND';
  END IF;
  
  RETURN v_card;
END;
$$;

COMMENT ON FUNCTION get_card_detail IS '獲取卡片詳情';

-- 獲取會員詳情
CREATE OR REPLACE FUNCTION get_member_detail(
  p_member_id uuid
)
RETURNS member_profiles
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member member_profiles%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT * INTO v_member FROM member_profiles WHERE id = p_member_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  RETURN v_member;
END;
$$;

COMMENT ON FUNCTION get_member_detail IS '獲取會員詳情';

-- 獲取卡片綁定列表
CREATE OR REPLACE FUNCTION get_card_bindings(
  p_card_id uuid
)
RETURNS TABLE(
  id uuid,
  member_id uuid,
  member_no text,
  member_name text,
  role bind_role,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  
  RETURN QUERY
  SELECT 
    cb.id,
    cb.member_id,
    mp.member_no,
    mp.name as member_name,
    cb.role,
    cb.created_at
  FROM card_bindings cb
  JOIN member_profiles mp ON mp.id = cb.member_id
  WHERE cb.card_id = p_card_id
  ORDER BY cb.created_at DESC;
END;
$$;

COMMENT ON FUNCTION get_card_bindings IS '獲取卡片綁定列表';

-- 搜尋會員
CREATE OR REPLACE FUNCTION search_members(
  p_keyword text,
  p_limit integer DEFAULT 50
)
RETURNS TABLE(
  id uuid,
  member_no text,
  name text,
  phone text,
  email text,
  status member_status,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
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
    mp.name ILIKE '%' || p_keyword || '%'
    OR mp.phone ILIKE '%' || p_keyword || '%'
    OR mp.email ILIKE '%' || p_keyword || '%'
    OR mp.member_no ILIKE '%' || p_keyword || '%'
  ORDER BY mp.created_at DESC
  LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION search_members IS '搜尋會員（需要 admin 權限）';

-- 搜尋商戶
CREATE OR REPLACE FUNCTION search_merchants(
  p_keyword text,
  p_limit integer DEFAULT 50
)
RETURNS TABLE(
  id uuid,
  code text,
  name text,
  contact text,
  status text,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  RETURN QUERY
  SELECT 
    m.id,
    m.code,
    m.name,
    m.contact,
    m.status,
    m.created_at
  FROM merchants m
  WHERE 
    m.name ILIKE '%' || p_keyword || '%'
    OR m.code ILIKE '%' || p_keyword || '%'
    OR m.contact ILIKE '%' || p_keyword || '%'
  ORDER BY m.created_at DESC
  LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION search_merchants IS '搜尋商戶（需要 admin 權限）';

-- 獲取積分記錄
CREATE OR REPLACE FUNCTION get_point_ledger(
  p_card_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0
)
RETURNS TABLE(
  id uuid,
  change int,
  balance_before int,
  balance_after int,
  reason text,
  tx_id uuid,
  created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  
  RETURN QUERY
  SELECT 
    pl.id,
    pl.change,
    pl.balance_before,
    pl.balance_after,
    pl.reason,
    pl.tx_id,
    pl.created_at
  FROM point_ledger pl
  WHERE pl.card_id = p_card_id
  ORDER BY pl.created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

COMMENT ON FUNCTION get_point_ledger IS '獲取積分記錄';

-- 更新結算狀態
CREATE OR REPLACE FUNCTION update_settlement_status(
  p_settlement_id uuid,
  p_status settlement_status
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  UPDATE settlements
  SET status = p_status,
      updated_at = now_utc()
  WHERE id = p_settlement_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'SETTLEMENT_NOT_FOUND';
  END IF;
  
  INSERT INTO audit.event_log(actor_user_id, action, object_type, object_id, context, happened_at)
  VALUES (auth.uid(), 'SETTLEMENT_STATUS_UPDATE', 'settlements', p_settlement_id,
          jsonb_build_object('new_status', p_status), now_utc());
  
  RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION update_settlement_status IS '更新結算狀態（需要 admin 權限）';

-- 獲取結算詳情
CREATE OR REPLACE FUNCTION get_settlement_detail(
  p_settlement_id uuid
)
RETURNS settlements
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_settlement settlements%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  SELECT * INTO v_settlement FROM settlements WHERE id = p_settlement_id;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'SETTLEMENT_NOT_FOUND';
  END IF;
  
  RETURN v_settlement;
END;
$$;

COMMENT ON FUNCTION get_settlement_detail IS '獲取結算詳情';

-- ============================================================================
