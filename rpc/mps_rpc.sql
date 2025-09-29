
-- ============================================================================
-- mps_rpc.sql  (Commercial Edition)
-- All RPCs are SECURITY DEFINER. Re-run safe: we drop then create.
-- Assumes schemas/tables from mps_schema.sql already exist.
-- ============================================================================

-- Helper: enforce search_path (expects sec.fixed_search_path() exists)
-- Note: All functions call PERFORM sec.fixed_search_path();

-- =======================
-- A) MEMBER & BINDINGS
-- =======================

DROP FUNCTION IF EXISTS app.create_member_profile(text, text, text, text, text, app.card_type) CASCADE;
CREATE OR REPLACE FUNCTION app.create_member_profile(
  p_name               text,
  p_phone              text,
  p_email              text,
  p_binding_user_org   text DEFAULT NULL,   -- e.g. 'wechat'
  p_binding_org_id     text DEFAULT NULL,   -- e.g. openid
  p_default_card_type  app.card_type DEFAULT 'standard'     -- always issues standard; arg reserved
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id  uuid := gen_random_uuid();
  v_card_id    uuid := gen_random_uuid();
BEGIN
  PERFORM sec.fixed_search_path();

  -- 1) Create member
  INSERT INTO app.member_profiles(id, name, phone, email, status, created_at, updated_at)
  VALUES (v_member_id, p_name, p_phone, p_email, 'active', app.now_utc(), app.now_utc());

  -- 2) Auto issue a STANDARD card (1:1; password NULL)
  INSERT INTO app.member_cards(id, card_no, member_owner_id, card_type, level, discount_rate, points, balance, status, created_at, updated_at, binding_password_hash)
  VALUES (v_card_id,
          app.gen_card_no('standard'),
          v_member_id,
          'standard',
          0,
          app.compute_discount(0),
          0,
          0,
          'active',
          app.now_utc(),
          app.now_utc(),
          NULL);

  -- 3) Bind owner (explicit binding table, if present)
  INSERT INTO app.card_bindings(card_id, member_id, role, created_at)
  VALUES (v_card_id, v_member_id, 'owner', app.now_utc());

  -- 4) Optional external identity binding
  IF p_binding_user_org IS NOT NULL AND p_binding_org_id IS NOT NULL THEN
    BEGIN
      INSERT INTO app.member_external_identities(member_id, provider, external_id, meta, created_at)
      VALUES (v_member_id, p_binding_user_org, p_binding_org_id, '{}'::jsonb, app.now_utc());
    EXCEPTION WHEN unique_violation THEN
      RAISE EXCEPTION 'EXTERNAL_ID_ALREADY_BOUND';
    END;
  END IF;

  -- 5) Audit
  PERFORM audit.log('CREATE_MEMBER', 'member_profiles', v_member_id,
                    jsonb_build_object('name', p_name, 'phone', p_phone, 'email', p_email));

  RETURN v_member_id;
END;
$$;

DROP FUNCTION IF EXISTS app.bind_member_to_card(uuid, uuid, app.bind_role, text) CASCADE;
CREATE OR REPLACE FUNCTION app.bind_member_to_card(
  p_card_id uuid,
  p_member_id uuid,
  p_role app.bind_role DEFAULT 'member',
  p_binding_password text DEFAULT NULL
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card app.member_cards%ROWTYPE;
  v_owner_password_hash text;
  v_owner_count int;
BEGIN
  PERFORM sec.fixed_search_path();

  SELECT * INTO v_card FROM app.member_cards WHERE id = p_card_id;
  IF NOT FOUND OR v_card.status <> 'active' THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND_OR_INACTIVE';
  END IF;

  -- Standard and voucher are non-shareable
  IF v_card.card_type IN ('standard','voucher') AND p_member_id <> v_card.member_owner_id THEN
    RAISE EXCEPTION 'CARD_TYPE_NOT_SHAREABLE';
  END IF;

  -- For prepaid/corporate: require password if defined
  IF v_card.card_type IN ('prepaid','corporate') THEN
    SELECT COUNT(*) INTO v_owner_count
    FROM app.card_bindings
    WHERE card_id = v_card.id AND role = 'owner';
    IF v_owner_count = 0 THEN
      RAISE EXCEPTION 'CARD_OWNER_NOT_DEFINED';
    END IF;

    IF v_card.binding_password_hash IS NOT NULL THEN
      IF p_binding_password IS NULL OR NOT (v_card.binding_password_hash = crypt(p_binding_password, v_card.binding_password_hash)) THEN
        RAISE EXCEPTION 'INVALID_BINDING_PASSWORD';
      END IF;
    END IF;
  END IF;

  -- Prevent duplicate role conflict
  INSERT INTO app.card_bindings(card_id, member_id, role, created_at)
  VALUES (p_card_id, p_member_id, p_role, app.now_utc())
  ON CONFLICT (card_id, member_id) DO UPDATE SET role = EXCLUDED.role;

  PERFORM audit.log('BIND_CARD', 'member_cards', p_card_id,
                    jsonb_build_object('member_id', p_member_id, 'role', p_role));
  RETURN TRUE;
END;
$$;

DROP FUNCTION IF EXISTS app.unbind_member_from_card(uuid, uuid) CASCADE;
CREATE OR REPLACE FUNCTION app.unbind_member_from_card(
  p_card_id uuid,
  p_member_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_owner_left int;
BEGIN
  PERFORM sec.fixed_search_path();

  DELETE FROM app.card_bindings
  WHERE card_id = p_card_id AND member_id = p_member_id;

  SELECT COUNT(*) INTO v_owner_left FROM app.card_bindings WHERE card_id = p_card_id AND role = 'owner';
  IF v_owner_left = 0 THEN
    RAISE EXCEPTION 'CANNOT_REMOVE_LAST_OWNER';
  END IF;

  PERFORM audit.log('UNBIND_CARD', 'member_cards', p_card_id, jsonb_build_object('member_id', p_member_id));
  RETURN TRUE;
END;
$$;

-- =======================
-- B) QR CODE MANAGEMENT
-- =======================

DROP FUNCTION IF EXISTS app.rotate_card_qr(uuid, integer) CASCADE;
CREATE OR REPLACE FUNCTION app.rotate_card_qr(
  p_card_id uuid,
  p_ttl_seconds integer DEFAULT 900
) RETURNS TABLE(qr_plain text, qr_expires_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_plain text := encode(gen_random_bytes(32),'base64');
  v_hash  text;
  v_expires timestamptz := app.now_utc() + make_interval(secs => GREATEST(p_ttl_seconds, 60));
BEGIN
  PERFORM sec.fixed_search_path();
  v_hash := crypt(v_plain, gen_salt('bf'));

  -- Upsert current QR state
  INSERT INTO app.card_qr_state(card_id, qr_hash, issued_at, expires_at)
  VALUES (p_card_id, v_hash, app.now_utc(), v_expires)
  ON CONFLICT (card_id) DO UPDATE
    SET qr_hash = EXCLUDED.qr_hash,
        issued_at = EXCLUDED.issued_at,
        expires_at = EXCLUDED.expires_at;

  -- Append history
  INSERT INTO app.card_qr_history(card_id, qr_hash, issued_at, expires_at)
  VALUES (p_card_id, v_hash, app.now_utc(), v_expires);

  PERFORM audit.log('QR_ROTATE','member_cards', p_card_id, jsonb_build_object('ttl', p_ttl_seconds));
  RETURN QUERY SELECT v_plain, v_expires;
END;
$$;

DROP FUNCTION IF EXISTS app.revoke_card_qr(uuid) CASCADE;
CREATE OR REPLACE FUNCTION app.revoke_card_qr(
  p_card_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  UPDATE app.card_qr_state SET expires_at = app.now_utc() WHERE card_id = p_card_id;
  PERFORM audit.log('QR_REVOKE','member_cards', p_card_id, '{}'::jsonb);
  RETURN TRUE;
END;
$$;

DROP FUNCTION IF EXISTS app.validate_qr_plain(text) CASCADE;
CREATE OR REPLACE FUNCTION app.validate_qr_plain(
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
  FROM app.card_qr_state s
  WHERE s.expires_at > app.now_utc()
    AND s.qr_hash = crypt(p_qr_plain, s.qr_hash)
  LIMIT 1;

  IF v_card_id IS NULL THEN
    RAISE EXCEPTION 'QR_EXPIRED_OR_INVALID';
  END IF;

  RETURN v_card_id;
END;
$$;

DROP FUNCTION IF EXISTS app.cron_rotate_qr_tokens(integer) CASCADE;
CREATE OR REPLACE FUNCTION app.cron_rotate_qr_tokens(
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
  v_expires timestamptz := app.now_utc() + make_interval(secs => GREATEST(p_ttl_seconds, 60));
BEGIN
  PERFORM sec.fixed_search_path();
  FOR r IN
    SELECT id FROM app.member_cards WHERE status='active' AND card_type IN ('prepaid','corporate')
  LOOP
    v_plain := encode(gen_random_bytes(32),'base64');
    v_hash := crypt(v_plain, gen_salt('bf'));
    INSERT INTO app.card_qr_state(card_id, qr_hash, issued_at, expires_at)
    VALUES (r.id, v_hash, app.now_utc(), v_expires)
    ON CONFLICT (card_id) DO UPDATE
      SET qr_hash = EXCLUDED.qr_hash,
          issued_at = EXCLUDED.issued_at,
          expires_at = EXCLUDED.expires_at;
    INSERT INTO app.card_qr_history(card_id, qr_hash, issued_at, expires_at)
    VALUES (r.id, v_hash, app.now_utc(), v_expires);
    v_cnt := v_cnt + 1;
  END LOOP;
  PERFORM audit.log('QR_CRON_ROTATE','system', NULL, jsonb_build_object('affected', v_cnt));
  RETURN v_cnt;
END;
$$;

-- =======================
-- C) PAYMENTS / REFUNDS / RECHARGE
-- =======================

DROP FUNCTION IF EXISTS app.merchant_charge_by_qr(text, text, numeric, text, jsonb, text) CASCADE;
CREATE OR REPLACE FUNCTION app.merchant_charge_by_qr(
  p_merchant_code text,
  p_qr_plain text,
  p_raw_amount numeric,
  p_idempotency_key text DEFAULT NULL,
  p_tag jsonb DEFAULT '{}'::jsonb,
  p_external_order_id text DEFAULT NULL
) RETURNS TABLE (tx_id uuid, tx_no text, card_id uuid, final_amount numeric, discount numeric)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merch app.merchants%ROWTYPE;
  v_is_user boolean;
  v_card app.member_cards%ROWTYPE;
  v_disc numeric(4,3) := 1.000;
  v_final numeric(12,2);
  v_tx_id uuid := gen_random_uuid();
  v_tx_no text;
  v_ref_exists uuid;
BEGIN
  PERFORM sec.fixed_search_path();

  IF p_raw_amount IS NULL OR p_raw_amount <= 0 THEN
    RAISE EXCEPTION 'INVALID_PRICE';
  END IF;

  SELECT * INTO v_merch FROM app.merchants WHERE code=p_merchant_code AND active=true;
  IF NOT FOUND THEN RAISE EXCEPTION 'MERCHANT_NOT_FOUND_OR_INACTIVE'; END IF;

  SELECT EXISTS(SELECT 1 FROM app.merchant_users WHERE merchant_id=v_merch.id AND user_id=auth.uid()) INTO v_is_user;
  IF NOT v_is_user THEN RAISE EXCEPTION 'NOT_MERCHANT_USER'; END IF;

  -- Validate QR -> card_id
  SELECT * INTO v_card FROM app.member_cards WHERE id = app.validate_qr_plain(p_qr_plain) FOR UPDATE;
  IF v_card.status <> 'active' THEN RAISE EXCEPTION 'CARD_NOT_ACTIVE'; END IF;
  IF v_card.expires_at IS NOT NULL AND v_card.expires_at < app.now_utc() THEN RAISE EXCEPTION 'CARD_EXPIRED'; END IF;

  -- Idempotency by key
  IF p_idempotency_key IS NOT NULL THEN
    BEGIN
      INSERT INTO app.idempotency_registry(idempotency_key, tx_id, created_at) VALUES (p_idempotency_key, v_tx_id, app.now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount, t.discount_applied
        FROM app.idempotency_registry ir
        JOIN app.transactions t ON t.id = ir.tx_id
        WHERE ir.idempotency_key = p_idempotency_key AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  -- Optional external order mapping
  IF p_external_order_id IS NOT NULL THEN
    BEGIN
      INSERT INTO app.merchant_order_registry(merchant_id, external_order_id, tx_id, created_at)
      VALUES (v_merch.id, p_external_order_id, v_tx_id, app.now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount, t.discount_applied
        FROM app.merchant_order_registry mo
        JOIN app.transactions t ON t.id = mo.tx_id
        WHERE mo.merchant_id=v_merch.id AND mo.external_order_id=p_external_order_id AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  -- Discount rule by card type
  IF v_card.card_type = 'standard' THEN
    v_disc := app.compute_discount(v_card.points);
  ELSIF v_card.card_type = 'prepaid' THEN
    v_disc := COALESCE(v_card.fixed_discount, app.compute_discount(v_card.points));
  ELSIF v_card.card_type = 'corporate' THEN
    v_disc := COALESCE(v_card.fixed_discount, 1.000);
  ELSE
    RAISE EXCEPTION 'UNSUPPORTED_CARD_TYPE_FOR_PAYMENT';
  END IF;

  v_final := round(p_raw_amount * v_disc, 2);
  IF v_card.balance < v_final THEN RAISE EXCEPTION 'INSUFFICIENT_BALANCE'; END IF;

  -- Lock by advisory
  PERFORM pg_advisory_xact_lock(sec.card_lock_key(v_card.id));

  -- Create tx number registry
  v_tx_no := app.gen_tx_no('payment');
  INSERT INTO app.tx_registry(tx_no, tx_id, created_at) VALUES (v_tx_no, v_tx_id, app.now_utc()) ON CONFLICT DO NOTHING;

  -- Insert transaction
  INSERT INTO app.transactions(id, tx_no, card_id, card_type, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned, status, tag, payment_method, created_at)
  VALUES (v_tx_id, v_tx_no, v_card.id, v_card.card_type, v_merch.id, 'payment',
    p_raw_amount, v_disc, v_final,
    CASE WHEN v_card.card_type IN ('standard','prepaid') THEN floor(p_raw_amount)::int ELSE 0 END,
    'processing', COALESCE(p_tag,'{}'::jsonb), 'balance', app.now_utc());

  -- Update balances / points
  UPDATE app.member_cards
  SET balance = balance - v_final,
      points  = CASE WHEN card_type IN ('standard','prepaid') THEN points + floor(p_raw_amount)::int ELSE points END,
      level   = CASE WHEN card_type IN ('standard','prepaid')
                      THEN app.compute_level(points + floor(p_raw_amount)::int)
                      ELSE level END,
      discount_rate = CASE WHEN card_type IN ('standard','prepaid')
                      THEN app.compute_discount(points + floor(p_raw_amount)::int)
                      ELSE discount_rate END,
      updated_at = app.now_utc()
  WHERE id = v_card.id;

  -- Point ledger
  IF v_card.card_type IN ('standard','prepaid') THEN
    INSERT INTO app.point_ledger(id, card_id, tx_id, change, balance_before, balance_after, reason, created_at)
    VALUES (gen_random_uuid(), v_card.id, v_tx_id, floor(p_raw_amount)::int, v_card.points,
            (SELECT points FROM app.member_cards WHERE id=v_card.id), 'payment_earn', app.now_utc());
  END IF;

  UPDATE app.transactions SET status='completed' WHERE id = v_tx_id;

  PERFORM audit.log('PAYMENT','transaction', v_tx_id, jsonb_build_object('merchant', v_merch.code, 'final', v_final));

  RETURN QUERY SELECT v_tx_id, v_tx_no, v_card.id, v_final, v_disc;
END;
$$;

DROP FUNCTION IF EXISTS app.merchant_refund_tx(text, text, numeric, jsonb) CASCADE;
CREATE OR REPLACE FUNCTION app.merchant_refund_tx(
  p_merchant_code text,
  p_original_tx_no text,
  p_refund_amount numeric,
  p_tag jsonb DEFAULT '{}'::jsonb
) RETURNS TABLE (refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merch app.merchants%ROWTYPE;
  v_is_user boolean;
  v_orig app.transactions%ROWTYPE;
  v_left numeric(12,2);
  v_ref_tx_id uuid := gen_random_uuid();
  v_ref_tx_no text;
BEGIN
  PERFORM sec.fixed_search_path();
  IF p_refund_amount IS NULL OR p_refund_amount <= 0 THEN RAISE EXCEPTION 'INVALID_REFUND_AMOUNT'; END IF;

  SELECT * INTO v_merch FROM app.merchants WHERE code=p_merchant_code AND active=true;
  IF NOT FOUND THEN RAISE EXCEPTION 'MERCHANT_NOT_FOUND_OR_INACTIVE'; END IF;

  SELECT EXISTS(SELECT 1 FROM app.merchant_users WHERE merchant_id=v_merch.id AND user_id=auth.uid()) INTO v_is_user;
  IF NOT v_is_user THEN RAISE EXCEPTION 'NOT_MERCHANT_USER'; END IF;

  SELECT * INTO v_orig FROM app.transactions WHERE tx_no=p_original_tx_no AND merchant_id=v_merch.id;
  IF NOT FOUND THEN RAISE EXCEPTION 'ORIGINAL_TX_NOT_FOUND'; END IF;
  IF v_orig.tx_type <> 'payment' OR v_orig.status NOT IN ('completed','refunded') THEN
    RAISE EXCEPTION 'ONLY_COMPLETED_PAYMENT_REFUNDABLE';
  END IF;

  SELECT v_orig.final_amount - COALESCE((
    SELECT SUM(final_amount) FROM app.transactions
    WHERE tx_type='refund' AND card_id=v_orig.card_id AND reason=v_orig.tx_no AND status IN ('processing','completed')
  ), 0)
  INTO v_left;
  IF v_left IS NULL THEN v_left := v_orig.final_amount; END IF;
  IF p_refund_amount > v_left THEN RAISE EXCEPTION 'REFUND_EXCEEDS_REMAINING'; END IF;

  -- Lock
  PERFORM pg_advisory_xact_lock(sec.card_lock_key(v_orig.card_id));

  v_ref_tx_no := app.gen_tx_no('refund');
  INSERT INTO app.tx_registry(tx_no, tx_id, created_at) VALUES (v_ref_tx_no, v_ref_tx_id, app.now_utc()) ON CONFLICT DO NOTHING;

  INSERT INTO app.transactions(id, tx_no, card_id, card_type, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned, status, tag, reason, payment_method, created_at)
  VALUES (v_ref_tx_id, v_ref_tx_no, v_orig.card_id, v_orig.card_type, v_merch.id, 'refund',
    p_refund_amount, 1.000, p_refund_amount, 0, 'processing', COALESCE(p_tag,'{}'::jsonb), v_orig.tx_no, v_orig.payment_method, app.now_utc());

  UPDATE app.member_cards SET balance = balance + p_refund_amount, updated_at = app.now_utc() WHERE id = v_orig.card_id;

  UPDATE app.transactions SET status='completed' WHERE id = v_ref_tx_id;

  IF p_refund_amount >= v_left THEN
    UPDATE app.transactions SET status='refunded' WHERE id = v_orig.id;
  END IF;

  PERFORM audit.log('REFUND','transaction', v_ref_tx_id, jsonb_build_object('merchant', v_merch.code, 'amount', p_refund_amount));

  RETURN QUERY SELECT v_ref_tx_id, v_ref_tx_no, p_refund_amount;
END;
$$;

DROP FUNCTION IF EXISTS app.user_recharge_card(uuid, numeric, app.pay_method, jsonb, text, text) CASCADE;
CREATE OR REPLACE FUNCTION app.user_recharge_card(
  p_card_id uuid,
  p_amount numeric,
  p_payment_method app.pay_method DEFAULT 'wechat',
  p_tag jsonb DEFAULT '{}'::jsonb,
  p_idempotency_key text DEFAULT NULL,
  p_external_order_id text DEFAULT NULL
) RETURNS TABLE (tx_id uuid, tx_no text, card_id uuid, amount numeric)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card app.member_cards%ROWTYPE;
  v_tx_id uuid := gen_random_uuid();
  v_tx_no text;
BEGIN
  PERFORM sec.fixed_search_path();
  IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_RECHARGE_AMOUNT'; END IF;

  SELECT * INTO v_card FROM app.member_cards WHERE id=p_card_id FOR UPDATE;
  IF NOT FOUND OR v_card.status <> 'active' THEN RAISE EXCEPTION 'CARD_NOT_FOUND_OR_INACTIVE'; END IF;
  IF v_card.card_type NOT IN ('prepaid','corporate') THEN
    RAISE EXCEPTION 'UNSUPPORTED_CARD_TYPE_FOR_RECHARGE';
  END IF;

  -- Idempotency
  IF p_idempotency_key IS NOT NULL THEN
    BEGIN
      INSERT INTO app.idempotency_registry(idempotency_key, tx_id, created_at) VALUES (p_idempotency_key, v_tx_id, app.now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount
        FROM app.idempotency_registry ir
        JOIN app.transactions t ON t.id = ir.tx_id
        WHERE ir.idempotency_key = p_idempotency_key AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  -- External order optional map
  IF p_external_order_id IS NOT NULL THEN
    BEGIN
      INSERT INTO app.merchant_order_registry(merchant_id, external_order_id, tx_id, created_at)
      VALUES (NULL, p_external_order_id, v_tx_id, app.now_utc());
    EXCEPTION WHEN unique_violation THEN
      RETURN QUERY
        SELECT t.id, t.tx_no, t.card_id, t.final_amount
        FROM app.merchant_order_registry mo
        JOIN app.transactions t ON t.id = mo.tx_id
        WHERE mo.merchant_id IS NULL AND mo.external_order_id = p_external_order_id AND t.status='completed'
        LIMIT 1;
      RETURN;
    END;
  END IF;

  v_tx_no := app.gen_tx_no('recharge');
  INSERT INTO app.tx_registry(tx_no, tx_id, created_at) VALUES (v_tx_no, v_tx_id, app.now_utc()) ON CONFLICT DO NOTHING;

  INSERT INTO app.transactions(id, tx_no, card_id, card_type, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned, status, tag, reason, payment_method, created_at)
  VALUES (v_tx_id, v_tx_no, v_card.id, v_card.card_type, NULL, 'recharge',
    p_amount, 1.000, p_amount, 0, 'processing', COALESCE(p_tag,'{}'::jsonb), 'recharge', p_payment_method, app.now_utc());

  UPDATE app.member_cards SET balance = balance + p_amount, updated_at = app.now_utc() WHERE id = v_card.id;

  UPDATE app.transactions SET status='completed' WHERE id = v_tx_id;

  PERFORM audit.log('RECHARGE','transaction', v_tx_id, jsonb_build_object('amount', p_amount, 'method', p_payment_method));

  RETURN QUERY SELECT v_tx_id, v_tx_no, v_card.id, p_amount;
END;
$$;

-- =======================
-- D) POINTS & LEVELS
-- =======================

DROP FUNCTION IF EXISTS app.update_points_and_level(uuid, int, text) CASCADE;
CREATE OR REPLACE FUNCTION app.update_points_and_level(
  p_card_id uuid,
  p_delta_points int,
  p_reason text DEFAULT 'manual_adjust'
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card app.member_cards%ROWTYPE;
  v_new_points int;
  v_new_level int;
  v_new_disc numeric(4,3);
BEGIN
  PERFORM sec.fixed_search_path();
  SELECT * INTO v_card FROM app.member_cards WHERE id=p_card_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'CARD_NOT_FOUND_OR_INACTIVE'; END IF;
  IF v_card.card_type NOT IN ('standard','prepaid') THEN
    RAISE EXCEPTION 'UNSUPPORTED_CARD_TYPE_FOR_POINTS';
  END IF;

  v_new_points := GREATEST(0, v_card.points + p_delta_points);
  v_new_level := app.compute_level(v_new_points);
  v_new_disc  := app.compute_discount(v_new_points);

  UPDATE app.member_cards
  SET points = v_new_points,
      level = v_new_level,
      discount_rate = v_new_disc,
      updated_at = app.now_utc()
  WHERE id = v_card.id;

  INSERT INTO app.point_ledger(id, card_id, tx_id, change, balance_before, balance_after, reason, created_at)
  VALUES (gen_random_uuid(), v_card.id, NULL, p_delta_points, v_card.points, v_new_points, p_reason, app.now_utc());

  PERFORM audit.log('POINTS_ADJUST','member_cards', v_card.id, jsonb_build_object('delta', p_delta_points, 'reason', p_reason));
  RETURN TRUE;
END;
$$;

-- =======================
-- E) ADMIN & RISK
-- =======================

DROP FUNCTION IF EXISTS app.freeze_card(uuid) CASCADE;
CREATE OR REPLACE FUNCTION app.freeze_card(
  p_card_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  UPDATE app.member_cards SET status='inactive', updated_at=app.now_utc() WHERE id=p_card_id;
  PERFORM audit.log('CARD_FREEZE','member_cards', p_card_id, '{}'::jsonb);
  RETURN TRUE;
END;
$$;

DROP FUNCTION IF EXISTS app.unfreeze_card(uuid) CASCADE;
CREATE OR REPLACE FUNCTION app.unfreeze_card(
  p_card_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  UPDATE app.member_cards SET status='active', updated_at=app.now_utc() WHERE id=p_card_id;
  PERFORM audit.log('CARD_UNFREEZE','member_cards', p_card_id, '{}'::jsonb);
  RETURN TRUE;
END;
$$;

DROP FUNCTION IF EXISTS app.admin_suspend_member(uuid) CASCADE;
CREATE OR REPLACE FUNCTION app.admin_suspend_member(
  p_member_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  UPDATE app.member_profiles SET status='suspended', updated_at=app.now_utc() WHERE id=p_member_id;
  PERFORM audit.log('MEMBER_SUSPEND','member_profiles', p_member_id, '{}'::jsonb);
  RETURN TRUE;
END;
$$;

DROP FUNCTION IF EXISTS app.admin_suspend_merchant(uuid) CASCADE;
CREATE OR REPLACE FUNCTION app.admin_suspend_merchant(
  p_merchant_id uuid
) RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  UPDATE app.merchants SET active=false, updated_at=app.now_utc() WHERE id=p_merchant_id;
  PERFORM audit.log('MERCHANT_SUSPEND','merchants', p_merchant_id, '{}'::jsonb);
  RETURN TRUE;
END;
$$;

-- =======================
-- F) SETTLEMENTS & QUERIES
-- =======================

DROP FUNCTION IF EXISTS app.generate_settlement(uuid, app.settlement_mode, timestamptz, timestamptz) CASCADE;
CREATE OR REPLACE FUNCTION app.generate_settlement(
  p_merchant_id uuid,
  p_mode app.settlement_mode,
  p_period_start timestamptz,
  p_period_end   timestamptz
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_id uuid := gen_random_uuid();
  v_total numeric(12,2);
  v_count bigint;
BEGIN
  PERFORM sec.fixed_search_path();

  SELECT COALESCE(SUM(CASE WHEN tx_type='payment' THEN final_amount ELSE -final_amount END),0),
         COUNT(*)
  INTO v_total, v_count
  FROM app.transactions
  WHERE merchant_id=p_merchant_id
    AND created_at >= p_period_start AND created_at < p_period_end
    AND status IN ('completed','refunded');

  INSERT INTO app.settlements(id, merchant_id, period_start, period_end, mode, total_amount, total_tx_count, status, created_at)
  VALUES (v_id, p_merchant_id, p_period_start, p_period_end, p_mode, v_total, v_count, 'pending', app.now_utc());

  PERFORM audit.log('SETTLEMENT_GENERATE','settlements', v_id,
    jsonb_build_object('merchant_id', p_merchant_id, 'total', v_total, 'count', v_count));

  RETURN v_id;
END;
$$;

DROP FUNCTION IF EXISTS app.list_settlements(uuid, integer, integer) CASCADE;
CREATE OR REPLACE FUNCTION app.list_settlements(
  p_merchant_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0
) RETURNS TABLE(id uuid, period_start timestamptz, period_end timestamptz, mode app.settlement_mode, total_amount numeric, total_tx_count bigint, status text, created_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  RETURN QUERY
  SELECT s.id, s.period_start, s.period_end, s.mode, s.total_amount, s.total_tx_count, s.status, s.created_at
  FROM app.settlements s
  WHERE s.merchant_id = p_merchant_id
  ORDER BY s.created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

DROP FUNCTION IF EXISTS app.get_member_transactions(uuid, integer, integer, timestamptz, timestamptz) CASCADE;
CREATE OR REPLACE FUNCTION app.get_member_transactions(
  p_member_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_start_date timestamptz DEFAULT NULL,
  p_end_date   timestamptz DEFAULT NULL
) RETURNS TABLE(id uuid, tx_no text, tx_type app.tx_type, card_id uuid, merchant_id uuid, final_amount numeric, status app.tx_status, created_at timestamptz, total_count bigint)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_where text := ' WHERE 1=1 ';
BEGIN
  PERFORM sec.fixed_search_path();
  RETURN QUERY
  WITH cte AS (
    SELECT t.* FROM app.transactions t
    JOIN app.member_cards c ON c.id = t.card_id
    WHERE c.member_owner_id = p_member_id
      AND (p_start_date IS NULL OR t.created_at >= p_start_date)
      AND (p_end_date   IS NULL OR t.created_at <  p_end_date)
  )
  SELECT id, tx_no, tx_type, card_id, merchant_id, final_amount, status, created_at,
         COUNT(*) OVER() AS total_count
  FROM cte
  ORDER BY created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

DROP FUNCTION IF EXISTS app.get_merchant_transactions(uuid, integer, integer, timestamptz, timestamptz) CASCADE;
CREATE OR REPLACE FUNCTION app.get_merchant_transactions(
  p_merchant_id uuid,
  p_limit integer DEFAULT 50,
  p_offset integer DEFAULT 0,
  p_start_date timestamptz DEFAULT NULL,
  p_end_date   timestamptz DEFAULT NULL
) RETURNS TABLE(id uuid, tx_no text, tx_type app.tx_type, card_id uuid, final_amount numeric, status app.tx_status, created_at timestamptz, total_count bigint)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  PERFORM sec.fixed_search_path();
  RETURN QUERY
  WITH cte AS (
    SELECT t.* FROM app.transactions t
    WHERE t.merchant_id = p_merchant_id
      AND (p_start_date IS NULL OR t.created_at >= p_start_date)
      AND (p_end_date   IS NULL OR t.created_at <  p_end_date)
  )
  SELECT id, tx_no, tx_type, card_id, final_amount, status, created_at,
         COUNT(*) OVER() AS total_count
  FROM cte
  ORDER BY created_at DESC
  LIMIT p_limit OFFSET p_offset;
END;
$$;

DROP FUNCTION IF EXISTS app.get_transaction_detail(text) CASCADE;
CREATE OR REPLACE FUNCTION app.get_transaction_detail(
  p_tx_no text
) RETURNS app.transactions
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_tx app.transactions%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  SELECT * INTO v_tx FROM app.transactions WHERE tx_no = p_tx_no;
  IF NOT FOUND THEN RAISE EXCEPTION 'TX_NOT_FOUND'; END IF;
  RETURN v_tx;
END;
$$;

-- ============================================================================
-- END OF FILE
-- ============================================================================
