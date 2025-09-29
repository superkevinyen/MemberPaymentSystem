-- ============================================================================
-- Member Payment System (MPS) - RPCs & Business Functions (Commercial)
-- Requires: mps_schema.sql already applied
-- Safe to re-run: each function is dropped before creation
-- ============================================================================

-- 0) Extensions (for crypt/hash)
create extension if not exists pgcrypto;

-- 1) Helpers (search_path, locks, level/discount)

-- 1.1 card_lock_key: map uuid -> bigint (for advisory locks)
drop function if exists app.card_lock_key(uuid);
create or replace function app.card_lock_key(p_card_id uuid)
returns bigint
language sql
immutable
as $$
  select ('x' || substr(p_card_id::text, 1, 15))::bit(60)::bigint
$$;

-- 1.2 compute_level(points)
drop function if exists app.compute_level(int);
create or replace function app.compute_level(p_points int)
returns int
language sql
stable
set search_path = app, public
as $$
  select coalesce((
    select level
      from app.membership_levels
     where is_active
       and p_points >= min_points
       and (max_points is null or p_points <= max_points)
     order by level desc
     limit 1
  ), 0)
$$;

-- 1.3 compute_discount(points)
drop function if exists app.compute_discount(int);
create or replace function app.compute_discount(p_points int)
returns numeric(4,3)
language sql
stable
set search_path = app, public
as $$
  select coalesce((
    select discount
      from app.membership_levels
     where is_active
       and p_points >= min_points
       and (max_points is null or p_points <= max_points)
     order by level desc
     limit 1
  ), 1.000)
$$;

-- 1.4 generate_qr_token_pair: (plain, hash)
drop function if exists app.generate_qr_token_pair();
create or replace function app.generate_qr_token_pair()
returns table(plain text, hash text)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare v_plain text;
begin
  v_plain := encode(gen_random_bytes(32), 'base64');  -- 256-bit
  return query select v_plain, crypt(v_plain, gen_salt('bf'));
end;
$$;

-- 2) Members & Bindings

-- 2.1 create_member_profile: 建會員 + 預設卡 + owner 綁定
drop function if exists app.create_member_profile(text, text, text, text, text, app.card_type);
create or replace function app.create_member_profile(
  p_name text,
  p_phone text,
  p_email text,
  p_binding_user_org text default null,
  p_binding_org_id  text default null,
  p_default_card_type app.card_type default 'standard'
) returns uuid
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_member_id uuid := gen_random_uuid();
  v_card_id uuid := gen_random_uuid();
  v_card_no text;
begin
  -- member
  insert into app.member_profiles(id, name, phone, email, binding_user_org, binding_org_id)
  values (v_member_id, p_name, p_phone, p_email, p_binding_user_org, p_binding_org_id);

  -- default card
  v_card_no := app.gen_card_no(p_default_card_type);
  insert into app.member_cards(id, card_no, card_type, owner_member_id, name, balance, points, level, discount, status)
  values (
    v_card_id, v_card_no, p_default_card_type, v_member_id,
    case when p_default_card_type='standard' then '標準會員卡' else upper(p_default_card_type::text) end,
    0, 0, app.compute_level(0), app.compute_discount(0), 'active'
  );

  -- owner binding（不強制密碼）
  insert into app.card_bindings(card_id, member_id, role, binding_password_hash)
  values (v_card_id, v_member_id, 'owner', null);

  -- audit
  insert into audit.event_log(action, object_type, object_id, context)
  values ('CREATE_MEMBER', 'member_profiles', v_member_id,
          jsonb_build_object('default_card_id', v_card_id, 'card_type', p_default_card_type));

  return v_member_id;
end;
$$;

-- 2.2 bind_external_identity: 綁定外部身份（upsert）
drop function if exists app.bind_external_identity(uuid, text, text, jsonb);
create or replace function app.bind_external_identity(
  p_member_id uuid,
  p_provider text,
  p_external_id text,
  p_meta jsonb default '{}'::jsonb
) returns boolean
language plpgsql
security definer
set search_path = app, audit, public
as $$
begin
  insert into app.member_external_identities(member_id, provider, external_id, meta)
  values (p_member_id, p_provider, p_external_id, coalesce(p_meta,'{}'::jsonb))
  on conflict (provider, external_id)
  do update set member_id = excluded.member_id, meta = excluded.meta, updated_at = app.now_utc();

  insert into audit.event_log(action, object_type, object_id, context)
  values ('BIND_EXTERNAL_ID', 'member_profiles', p_member_id,
          jsonb_build_object('provider', p_provider, 'external_id', p_external_id));
  return true;
end;
$$;

-- 2.3 bind_member_to_card: 多人共享綁定
-- 設計：若卡已存在 owner 且其 binding_password_hash 不為 null，需驗證密碼。
-- 若卡尚無 owner 綁定，允許第一位呼叫者成為 owner（僅限與卡 owner_member_id 相同的 member）。
drop function if exists app.bind_member_to_card(uuid, uuid, app.bind_role, text);
create or replace function app.bind_member_to_card(
  p_card_id uuid,
  p_member_id uuid,
  p_role app.bind_role default 'member',
  p_binding_password text default null
) returns boolean
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_owner_hash text;
  v_owner_member uuid;
  v_exists boolean;
begin
  -- 檢查卡存在
  perform 1 from app.member_cards where id = p_card_id and status='active';
  if not found then raise exception 'CARD_NOT_FOUND_OR_INACTIVE'; end if;

  -- 檢查是否已綁定
  select exists(select 1 from app.card_bindings where card_id=p_card_id and member_id=p_member_id) into v_exists;
  if v_exists then
    return true; -- idempotent
  end if;

  -- 取得 owner 與其密碼
  select cb.binding_password_hash, mc.owner_member_id
    into v_owner_hash, v_owner_member
  from app.member_cards mc
  left join app.card_bindings cb on cb.card_id = mc.id and cb.role='owner'
  where mc.id = p_card_id
  limit 1;

  if v_owner_member is null then
    raise exception 'CARD_OWNER_NOT_DEFINED';
  end if;

  -- 若已存在 owner 的密碼，必須驗證
  if v_owner_hash is not null then
    if p_binding_password is null or not (v_owner_hash = crypt(p_binding_password, v_owner_hash)) then
      raise exception 'INVALID_BINDING_PASSWORD';
    end if;
  else
    -- 未設密碼：僅當呼叫者欲以 owner 身份綁定，且 member_id 等於卡 owner_member_id
    if p_role='owner' and p_member_id <> v_owner_member then
      raise exception 'ONLY_OWNER_MEMBER_CAN_CLAIM_OWNER_ROLE';
    end if;
  end if;

  insert into app.card_bindings(card_id, member_id, role, binding_password_hash)
  values (p_card_id, p_member_id, p_role,
          case when p_role='owner' and p_binding_password is not null
               then crypt(p_binding_password, gen_salt('bf')) else null end)
  on conflict (card_id, member_id) do nothing;

  insert into audit.event_log(action, object_type, object_id, context)
  values ('BIND', 'member_card', p_card_id, jsonb_build_object('member_id', p_member_id, 'role', p_role));
  return true;
end;
$$;

-- 2.4 unbind_member_from_card
drop function if exists app.unbind_member_from_card(uuid, uuid);
create or replace function app.unbind_member_from_card(
  p_card_id uuid,
  p_member_id uuid
) returns boolean
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_is_owner boolean;
  v_owner_count int;
begin
  select (role='owner') into v_is_owner
  from app.card_bindings where card_id=p_card_id and member_id=p_member_id;

  if not found then
    return true; -- idempotent
  end if;

  if v_is_owner then
    -- 不允許移除最後一位 owner
    select count(*) into v_owner_count from app.card_bindings where card_id=p_card_id and role='owner';
    if v_owner_count <= 1 then
      raise exception 'CANNOT_REMOVE_LAST_OWNER';
    end if;
  end if;

  delete from app.card_bindings where card_id=p_card_id and member_id=p_member_id;

  insert into audit.event_log(action, object_type, object_id, context)
  values ('UNBIND', 'member_card', p_card_id, jsonb_build_object('member_id', p_member_id));
  return true;
end;
$$;

-- 3) QR Code

-- 3.1 rotate_card_qr
drop function if exists app.rotate_card_qr(uuid, int);
create or replace function app.rotate_card_qr(
  p_card_id uuid,
  p_ttl_seconds int default 900
) returns table(qr_plain text, qr_expires_at timestamptz)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_card app.member_cards%rowtype;
  v_plain text;
  v_hash text;
  v_expires timestamptz;
begin
  select * into v_card from app.member_cards where id = p_card_id for update;
  if not found then raise exception 'CARD_NOT_FOUND'; end if;
  if v_card.status <> 'active' then raise exception 'CARD_NOT_ACTIVE'; end if;

  select plain, hash into v_plain, v_hash from app.generate_qr_token_pair();
  v_expires := app.now_utc() + make_interval(secs => greatest(60, p_ttl_seconds));

  insert into app.card_qr_state(card_id, token_hash, expires_at, updated_at)
  values (p_card_id, v_hash, v_expires, app.now_utc())
  on conflict (card_id)
  do update set token_hash = excluded.token_hash,
                expires_at = excluded.expires_at,
                updated_at = app.now_utc();

  insert into app.card_qr_history(card_id, token_hash, expires_at, issued_by)
  values (p_card_id, v_hash, v_expires, null);

  insert into audit.event_log(action, object_type, object_id, context)
  values ('QR_ROTATE', 'member_card', p_card_id, jsonb_build_object('expires_at', v_expires));

  return query select v_plain, v_expires;
end;
$$;

-- 3.2 validate_qr_plain: return card_id or exception
drop function if exists app.validate_qr_plain(text);
create or replace function app.validate_qr_plain(
  p_qr_plain text
) returns uuid
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_rec record;
begin
  if p_qr_plain is null or length(p_qr_plain) < 16 then
    raise exception 'INVALID_QR';
  end if;

  for v_rec in
    select card_id, token_hash, expires_at
      from app.card_qr_state
     where expires_at >= app.now_utc()
  loop
    if v_rec.token_hash = crypt(p_qr_plain, v_rec.token_hash) then
      return v_rec.card_id;
    end if;
  end loop;

  raise exception 'QR_EXPIRED_OR_INVALID';
end;
$$;

-- 3.3 revoke_card_qr: 立即失效
drop function if exists app.revoke_card_qr(uuid);
create or replace function app.revoke_card_qr(p_card_id uuid)
returns boolean
language plpgsql
security definer
set search_path = app, audit, public
as $$
begin
  update app.card_qr_state
     set expires_at = app.now_utc(), updated_at = app.now_utc()
   where card_id = p_card_id;
  insert into audit.event_log(action, object_type, object_id, context)
  values ('QR_REVOKE', 'member_card', p_card_id, '{}'::jsonb);
  return true;
end;
$$;

-- 3.4 cron_rotate_qr_tokens: for prepaid/corporate 批量輪換
drop function if exists app.cron_rotate_qr_tokens(int);
create or replace function app.cron_rotate_qr_tokens(
  p_ttl_seconds int default 300
) returns int
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_cnt int := 0;
  v_plain text;
  v_hash text;
  v_expires timestamptz;
  v_card_id uuid;
begin
  for v_card_id in
    select id from app.member_cards
     where status='active' and card_type in ('prepaid','corporate')
  loop
    select plain, hash into v_plain, v_hash from app.generate_qr_token_pair();
    v_expires := app.now_utc() + make_interval(secs => greatest(60, p_ttl_seconds));

    insert into app.card_qr_state(card_id, token_hash, expires_at, updated_at)
    values (v_card_id, v_hash, v_expires, app.now_utc())
    on conflict (card_id)
    do update set token_hash = excluded.token_hash,
                  expires_at = excluded.expires_at,
                  updated_at = app.now_utc();

    insert into app.card_qr_history(card_id, token_hash, expires_at, issued_by)
    values (v_card_id, v_hash, v_expires, null);

    v_cnt := v_cnt + 1;
  end loop;

  insert into audit.event_log(action, object_type, object_id, context)
  values ('QR_CRON_ROTATE', 'system', null, jsonb_build_object('affected', v_cnt));
  return v_cnt;
end;
$$;

-- 4) Payments / Refunds / Recharge

-- 4.1 merchant_charge_by_qr
drop function if exists app.merchant_charge_by_qr(text, text, numeric, text, jsonb, text);
create or replace function app.merchant_charge_by_qr(
  p_merchant_code text,
  p_qr_plain text,
  p_raw_amount numeric,
  p_idempotency_key text default null,
  p_tag jsonb default '{}'::jsonb,
  p_external_order_id text default null
) returns table (tx_id uuid, tx_no text, card_id uuid, final_amount numeric, discount numeric)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_merch app.merchants%rowtype;
  v_is_merch_user boolean;
  v_card app.member_cards%rowtype;
  v_card_id uuid;
  v_lock_key bigint;
  v_disc numeric(4,3) := 1.000;
  v_final numeric(12,2);
  v_tx_id uuid := gen_random_uuid();
  v_tx_no text;
  v_points int;
begin
  if p_raw_amount is null or p_raw_amount <= 0 then raise exception 'INVALID_PRICE'; end if;
  if p_qr_plain is null or length(p_qr_plain) < 16 then raise exception 'INVALID_QR'; end if;

  select * into v_merch from app.merchants where code=p_merchant_code and status='active';
  if not found then raise exception 'MERCHANT_NOT_FOUND_OR_INACTIVE'; end if;

  -- 檢查呼叫者是否為商戶成員
  select exists(
    select 1 from app.merchant_users mu where mu.merchant_id=v_merch.id and mu.auth_user_id=auth.uid()
  ) into v_is_merch_user;
  if not v_is_merch_user then raise exception 'NOT_MERCHANT_USER'; end if;

  -- 解析 QR -> card_id
  v_card_id := app.validate_qr_plain(p_qr_plain);

  -- lock & load
  v_lock_key := app.card_lock_key(v_card_id);
  perform pg_advisory_xact_lock(v_lock_key);

  select * into v_card from app.member_cards where id=v_card_id for update;
  if not found then raise exception 'CARD_NOT_FOUND'; end if;
  if v_card.status <> 'active' then raise exception 'CARD_NOT_ACTIVE'; end if;
  if v_card.expires_at is not null and v_card.expires_at < app.now_utc() then
    raise exception 'CARD_EXPIRED';
  end if;

  -- idempotency（若已存在完成交易，直接回傳）
  if p_idempotency_key is not null then
    begin
      insert into app.idempotency_registry(idempotency_key, tx_id)
      values (p_idempotency_key, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount, t.discount_applied
          from app.idempotency_registry ir
          join app.transactions t on t.id = ir.tx_id
         where ir.idempotency_key = p_idempotency_key
           and t.status='completed'
         limit 1;
      return;
    end;
  end if;

  -- external order registry（可選）
  if p_external_order_id is not null then
    begin
      insert into app.merchant_order_registry(merchant_id, external_order_id, tx_id)
      values (v_merch.id, p_external_order_id, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount, t.discount_applied
          from app.merchant_order_registry mo
          join app.transactions t on t.id = mo.tx_id
         where mo.merchant_id = v_merch.id
           and mo.external_order_id = p_external_order_id
           and t.status='completed'
         limit 1;
      return;
    end;
  end if;

  -- 計算折扣
  if v_card.card_type = 'standard' then
    v_disc  := app.compute_discount(v_card.points);
  elsif v_card.card_type = 'prepaid' then
    v_disc  := coalesce(v_card.fixed_discount, app.compute_discount(v_card.points));
  elsif v_card.card_type = 'corporate' then
    v_disc  := coalesce(v_card.fixed_discount, 1.000);
  else
    raise exception 'UNSUPPORTED_CARD_TYPE_FOR_PAYMENT';
  end if;

  v_final := round(p_raw_amount * v_disc, 2);
  if v_card.balance < v_final then raise exception 'INSUFFICIENT_BALANCE'; end if;

  -- 建立交易（processing）
  v_tx_no := app.gen_tx_no('payment');

  insert into app.tx_registry(tx_no, tx_id) values (v_tx_no, v_tx_id)
  on conflict (tx_no) do nothing;

  v_points := floor(p_raw_amount)::int;

  insert into app.transactions(
    id, tx_no, tx_type, card_id, merchant_id,
    raw_amount, discount_applied, final_amount, points_earned, status,
    reason, payment_method, external_order_id, idempotency_key, processed_by_user_id, tag
  ) values (
    v_tx_id, v_tx_no, 'payment', v_card_id, v_merch.id,
    p_raw_amount, v_disc, v_final, case when v_card.card_type in ('standard','prepaid') then v_points else 0 end, 'processing',
    null, 'balance', p_external_order_id, p_idempotency_key, auth.uid(), coalesce(p_tag,'{}'::jsonb)
  );

  -- 更新餘額/積分/等級
  update app.member_cards
     set balance = balance - v_final,
         points  = case when v_card.card_type in ('standard','prepaid') then points + v_points else points end,
         level   = case when v_card.card_type in ('standard','prepaid')
                        then app.compute_level(points + v_points)
                        else level end,
         discount= case when v_card.card_type in ('standard','prepaid')
                        then app.compute_discount(points)
                        else coalesce(fixed_discount, discount) end,
         updated_at = app.now_utc()
   where id = v_card_id;

  -- 完成交易
  update app.transactions set status='completed', updated_at=app.now_utc() where id = v_tx_id;

  -- 審計
  insert into audit.event_log(action, object_type, object_id, context)
  values ('PAYMENT', 'transaction', v_tx_id,
          jsonb_build_object('merchant', v_merch.code, 'final', v_final, 'card_id', v_card_id));

  return query select v_tx_id, v_tx_no, v_card_id, v_final, v_disc;
end;
$$;

-- 4.2 merchant_refund_tx
drop function if exists app.merchant_refund_tx(text, text, numeric, jsonb);
create or replace function app.merchant_refund_tx(
  p_merchant_code text,
  p_original_tx_no text,
  p_refund_amount numeric,
  p_tag jsonb default '{}'::jsonb
) returns table (refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_merch app.merchants%rowtype;
  v_is_merch_user boolean;
  v_orig app.transactions%rowtype;
  v_card app.member_cards%rowtype;
  v_ref_left numeric(12,2);
  v_ref_tx_id uuid := gen_random_uuid();
  v_ref_tx_no text;
  v_lock_key bigint;
begin
  if p_refund_amount is null or p_refund_amount <= 0 then raise exception 'INVALID_REFUND_AMOUNT'; end if;

  select * into v_merch from app.merchants where code=p_merchant_code and status='active';
  if not found then raise exception 'MERCHANT_NOT_FOUND_OR_INACTIVE'; end if;

  select exists(select 1 from app.merchant_users where merchant_id=v_merch.id and auth_user_id=auth.uid())
    into v_is_merch_user;
  if not v_is_merch_user then raise exception 'NOT_MERCHANT_USER'; end if;

  select * into v_orig from app.transactions where tx_no=p_original_tx_no and merchant_id=v_merch.id;
  if not found then raise exception 'ORIGINAL_TX_NOT_FOUND'; end if;
  if v_orig.tx_type<>'payment' or v_orig.status not in ('completed','refunded') then
    raise exception 'ONLY_COMPLETED_PAYMENT_REFUNDABLE';
  end if;
  if v_orig.status='refunded' then
    -- 仍允許部分退款紀錄存在，但左邊可能=0
    null;
  end if;

  -- 剩餘可退
  select v_orig.final_amount - coalesce(sum(final_amount),0)
    into v_ref_left
  from app.transactions
  where original_tx_id = v_orig.id
    and tx_type = 'refund'
    and status in ('processing','completed');
  if v_ref_left is null then v_ref_left := v_orig.final_amount; end if;
  if p_refund_amount > v_ref_left then raise exception 'REFUND_EXCEEDS_REMAINING'; end if;

  -- lock card
  select * into v_card from app.member_cards where id=v_orig.card_id for update;
  if not found then raise exception 'CARD_NOT_FOUND'; end if;

  v_lock_key := app.card_lock_key(v_orig.card_id);
  perform pg_advisory_xact_lock(v_lock_key);

  -- 建立退款交易
  v_ref_tx_no := app.gen_tx_no('refund');
  insert into app.tx_registry(tx_no, tx_id) values (v_ref_tx_no, v_ref_tx_id)
  on conflict (tx_no) do nothing;

  insert into app.transactions(
    id, tx_no, tx_type, card_id, merchant_id,
    raw_amount, discount_applied, final_amount, points_earned, status,
    reason, payment_method, original_tx_id, processed_by_user_id, tag
  ) values (
    v_ref_tx_id, v_ref_tx_no, 'refund', v_orig.card_id, v_merch.id,
    p_refund_amount, 1.000, p_refund_amount, 0, 'processing',
    v_orig.tx_no, v_orig.payment_method, v_orig.id, auth.uid(), coalesce(p_tag,'{}'::jsonb)
  );

  -- 回補餘額
  update app.member_cards set balance = balance + p_refund_amount, updated_at=app.now_utc()
   where id = v_orig.card_id;

  update app.transactions set status='completed', updated_at=app.now_utc() where id = v_ref_tx_id;

  -- 若已全退，標示原交易 refunded
  if p_refund_amount >= v_ref_left then
    update app.transactions set status='refunded', updated_at=app.now_utc() where id = v_orig.id;
  end if;

  insert into audit.event_log(action, object_type, object_id, context)
  values ('REFUND', 'transaction', v_ref_tx_id,
          jsonb_build_object('merchant', v_merch.code, 'amount', p_refund_amount, 'original', v_orig.tx_no));

  return query select v_ref_tx_id, v_ref_tx_no, p_refund_amount;
end;
$$;

-- 4.3 user_recharge_card
drop function if exists app.user_recharge_card(uuid, numeric, app.pay_method, jsonb, text, text);
create or replace function app.user_recharge_card(
  p_card_id uuid,
  p_amount numeric,
  p_payment_method app.pay_method default 'wechat',
  p_tag jsonb default '{}'::jsonb,
  p_idempotency_key text default null,
  p_external_order_id text default null
) returns table (tx_id uuid, tx_no text, card_id uuid, amount numeric)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_card app.member_cards%rowtype;
  v_tx_id uuid := gen_random_uuid();
  v_tx_no text;
begin
  if p_amount is null or p_amount <= 0 then raise exception 'INVALID_RECHARGE_AMOUNT'; end if;

  -- idempotency
  if p_idempotency_key is not null then
    begin
      insert into app.idempotency_registry(idempotency_key, tx_id) values (p_idempotency_key, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount
          from app.idempotency_registry ir
          join app.transactions t on t.id=ir.tx_id
         where ir.idempotency_key=p_idempotency_key
           and t.status='completed'
         limit 1;
      return;
    end;
  end if;

  -- external order
  if p_external_order_id is not null then
    begin
      insert into app.merchant_order_registry(merchant_id, external_order_id, tx_id)
      values (null, p_external_order_id, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount
          from app.merchant_order_registry mo
          join app.transactions t on t.id=mo.tx_id
         where mo.merchant_id is null
           and mo.external_order_id=p_external_order_id
           and t.status='completed'
         limit 1;
      return;
    end;
  end if;

  select * into v_card from app.member_cards where id=p_card_id and status='active' for update;
  if not found then raise exception 'CARD_NOT_FOUND_OR_INACTIVE'; end if;

  v_tx_no := app.gen_tx_no('recharge');
  insert into app.tx_registry(tx_no, tx_id) values (v_tx_no, v_tx_id)
  on conflict (tx_no) do nothing;

  insert into app.transactions(
    id, tx_no, tx_type, card_id, merchant_id,
    raw_amount, discount_applied, final_amount, points_earned, status,
    reason, payment_method, external_order_id, idempotency_key, processed_by_user_id, tag
  ) values (
    v_tx_id, v_tx_no, 'recharge', p_card_id, null,
    p_amount, 1.000, p_amount, 0, 'processing',
    'user_recharge', p_payment_method, p_external_order_id, p_idempotency_key, auth.uid(), coalesce(p_tag,'{}'::jsonb)
  );

  update app.member_cards set balance = balance + p_amount, updated_at=app.now_utc()
   where id = p_card_id;

  update app.transactions set status='completed', updated_at=app.now_utc() where id=v_tx_id;

  insert into audit.event_log(action, object_type, object_id, context)
  values ('RECHARGE', 'transaction', v_tx_id, jsonb_build_object('amount', p_amount, 'method', p_payment_method));

  return query select v_tx_id, v_tx_no, p_card_id, p_amount;
end;
$$;

-- 5) Points & Level

-- 5.1 update_points_and_level
drop function if exists app.update_points_and_level(uuid, int, text);
create or replace function app.update_points_and_level(
  p_card_id uuid,
  p_delta_points int,
  p_reason text default 'manual_adjust'
) returns boolean
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_card app.member_cards%rowtype;
  v_before int;
  v_after int;
begin
  select * into v_card from app.member_cards where id=p_card_id for update;
  if not found then raise exception 'CARD_NOT_FOUND'; end if;

  v_before := v_card.points;
  v_after := greatest(0, v_card.points + p_delta_points);

  update app.member_cards
     set points = v_after,
         level  = app.compute_level(v_after),
         discount = case when v_card.card_type in ('standard','prepaid')
                         then app.compute_discount(v_after)
                         else coalesce(fixed_discount, discount) end,
         updated_at = app.now_utc()
   where id = p_card_id;

  insert into app.point_ledger(card_id, tx_id, change, balance_before, balance_after, reason, created_at)
  values (p_card_id, null, p_delta_points, v_before, v_after, p_reason, app.now_utc());

  insert into audit.event_log(action, object_type, object_id, context)
  values ('POINTS_ADJUST', 'member_card', p_card_id, jsonb_build_object('delta', p_delta_points));
  return true;
end;
$$;

-- 6) Settlements & Reports

-- 6.1 generate_settlement
drop function if exists app.generate_settlement(uuid, app.settlement_mode, timestamptz, timestamptz);
create or replace function app.generate_settlement(
  p_merchant_id uuid,
  p_mode app.settlement_mode,
  p_period_start timestamptz,
  p_period_end timestamptz
) returns uuid
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_is_merch_user boolean;
  v_settlement_id uuid := gen_random_uuid();
  v_total numeric(12,2);
  v_count int;
  v_payload jsonb;
begin
  if p_period_start is null or p_period_end is null or p_period_end <= p_period_start then
    raise exception 'INVALID_PERIOD';
  end if;

  -- 呼叫者需為該商戶成員
  select exists(select 1 from app.merchant_users where merchant_id=p_merchant_id and auth_user_id=auth.uid())
    into v_is_merch_user;
  if not v_is_merch_user then raise exception 'NOT_MERCHANT_USER'; end if;

  -- 計算淨額（payment - refund）
  select coalesce(sum(
           case when tx_type='payment' then final_amount
                when tx_type='refund'  then -final_amount
                else 0 end
         ), 0) as total,
         count(*)::int
    into v_total, v_count
  from app.transactions
  where merchant_id = p_merchant_id
    and created_at >= p_period_start
    and created_at <  p_period_end
    and status in ('completed','refunded');

  -- payload：各類聚合（可擴充）
  select jsonb_build_object(
           'payments',   coalesce(sum(case when tx_type='payment' then final_amount else 0 end),0),
           'refunds',    coalesce(sum(case when tx_type='refund'  then final_amount else 0 end),0),
           'tx_count',   count(*)
         )
    into v_payload
  from app.transactions
  where merchant_id = p_merchant_id
    and created_at >= p_period_start
    and created_at <  p_period_end
    and status in ('completed','refunded');

  insert into app.settlements(id, merchant_id, mode, period_start, period_end, total_amount, total_tx_count, status, payload)
  values (v_settlement_id, p_merchant_id, p_mode, p_period_start, p_period_end, v_total, v_count, 'pending', v_payload);

  insert into audit.event_log(action, object_type, object_id, context)
  values ('SETTLEMENT_GENERATE', 'settlement', v_settlement_id,
          jsonb_build_object('merchant_id', p_merchant_id, 'mode', p_mode));

  return v_settlement_id;
end;
$$;

-- 6.2 list_settlements
drop function if exists app.list_settlements(uuid, int, int);
create or replace function app.list_settlements(
  p_merchant_id uuid,
  p_limit int default 50,
  p_offset int default 0
) returns table(id uuid, period_start timestamptz, period_end timestamptz, total_amount numeric, total_tx_count int, status app.settlement_status, created_at timestamptz)
language sql
security definer
set search_path = app, audit, public
as $$
  select s.id, s.period_start, s.period_end, s.total_amount, s.total_tx_count, s.status, s.created_at
    from app.settlements s
   where s.merchant_id = p_merchant_id
   order by s.period_start desc
   limit p_limit offset p_offset
$$;

-- 6.3 get_member_transactions
drop function if exists app.get_member_transactions(uuid, int, int, timestamptz, timestamptz);
create or replace function app.get_member_transactions(
  p_member_id uuid,
  p_limit int default 50,
  p_offset int default 0,
  p_start_date timestamptz default null,
  p_end_date   timestamptz default null
) returns table(
  id uuid, tx_no text, tx_type app.tx_type, card_id uuid, merchant_id uuid,
  final_amount numeric, status app.tx_status, created_at timestamptz, total_count bigint
)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_where text := '';
begin
  v_where := ' where card_id in (select id from app.member_cards where owner_member_id = '||quote_literal(p_member_id)||' or id in (select card_id from app.card_bindings where member_id = '||quote_literal(p_member_id)||'))';
  if p_start_date is not null then
    v_where := v_where || ' and created_at >= '||quote_literal(p_start_date);
  end if;
  if p_end_date is not null then
    v_where := v_where || ' and created_at < '||quote_literal(p_end_date);
  end if;

  return query execute format(
    'select id, tx_no, tx_type, card_id, merchant_id, final_amount, status, created_at, count(*) over() as total_count
       from app.transactions %s
      order by created_at desc
      limit %s offset %s', v_where, p_limit, p_offset
  );
end;
$$;

-- 6.4 get_merchant_transactions
drop function if exists app.get_merchant_transactions(uuid, int, int, timestamptz, timestamptz);
create or replace function app.get_merchant_transactions(
  p_merchant_id uuid,
  p_limit int default 50,
  p_offset int default 0,
  p_start_date timestamptz default null,
  p_end_date   timestamptz default null
) returns table(
  id uuid, tx_no text, tx_type app.tx_type, card_id uuid, final_amount numeric,
  status app.tx_status, created_at timestamptz, total_count bigint
)
language plpgsql
security definer
set search_path = app, audit, public
as $$
declare
  v_where text := ' where merchant_id = '||quote_literal(p_merchant_id);
begin
  if p_start_date is not null then
    v_where := v_where || ' and created_at >= '||quote_literal(p_start_date);
  end if;
  if p_end_date is not null then
    v_where := v_where || ' and created_at < '||quote_literal(p_end_date);
  end if;

  return query execute format(
    'select id, tx_no, tx_type, card_id, final_amount, status, created_at, count(*) over() as total_count
       from app.transactions %s
      order by created_at desc
      limit %s offset %s', v_where, p_limit, p_offset
  );
end;
$$;

-- 6.5 get_transaction_detail
drop function if exists app.get_transaction_detail(text);
create or replace function app.get_transaction_detail(
  p_tx_no text
) returns app.transactions
language sql
security definer
set search_path = app, audit, public
as $$
  select * from app.transactions where tx_no = p_tx_no limit 1
$$;

-- 7) Card / Member / Merchant admin helpers

-- 7.1 freeze_card / unfreeze_card
drop function if exists app.freeze_card(uuid);
create or replace function app.freeze_card(p_card_id uuid)
returns boolean
language sql
security definer
set search_path = app, audit, public
as $$
  update app.member_cards set status='suspended', updated_at=app.now_utc()
   where id = p_card_id;
  select true
$$;

drop function if exists app.unfreeze_card(uuid);
create or replace function app.unfreeze_card(p_card_id uuid)
returns boolean
language sql
security definer
set search_path = app, audit, public
as $$
  update app.member_cards set status='active', updated_at=app.now_utc()
   where id = p_card_id;
  select true
$$;

-- 7.2 admin_suspend_member / admin_suspend_merchant
drop function if exists app.admin_suspend_member(uuid);
create or replace function app.admin_suspend_member(p_member_id uuid)
returns boolean
language sql
security definer
set search_path = app, audit, public
as $$
  update app.member_profiles set status='suspended', updated_at=app.now_utc()
   where id = p_member_id;
  select true
$$;

drop function if exists app.admin_suspend_merchant(uuid);
create or replace function app.admin_suspend_merchant(p_merchant_id uuid)
returns boolean
language sql
security definer
set search_path = app, audit, public
as $$
  update app.merchants set status='inactive', updated_at=app.now_utc()
   where id = p_merchant_id;
  select true
$$;

-- ============================================================================
-- END OF RPCs
-- ============================================================================
