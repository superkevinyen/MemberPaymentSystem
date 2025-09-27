-- ============================================================================
-- MemberPaymentSystem - FULL (Plan A: Per-Partition Uniques + Global Registries)
-- Schemas: app (biz), audit (logs), sec (security helpers)
-- Notes:
-- - Transactions partitioned monthly by created_at
-- - No global PK/UNIQUE on parent; per-partition unique indexes
-- - Global uniqueness via small registry tables (tx_no, idempotency_key, merchant+external_order_id)
-- - QR code stored as bcrypt hash (no plaintext at rest), 15-min validity
-- - Strict RLS (default deny); writes only via SECURITY DEFINER RPCs
-- ============================================================================

-----------------------
-- 0) Extensions & Schemas
-----------------------
create extension if not exists "pgcrypto";

create schema if not exists app;
create schema if not exists audit;
create schema if not exists sec;

revoke all on schema app   from public;
revoke all on schema audit from public;
revoke all on schema sec   from public;

-----------------------
-- 1) Types & Sequences
-----------------------
do $$ begin
  create type app.card_type as enum ('personal','enterprise');
exception when duplicate_object then null; end $$;

do $$ begin
  create type app.tx_type as enum ('payment','refund','recharge');
exception when duplicate_object then null; end $$;

do $$ begin
  create type app.tx_status as enum ('processing','completed','failed','cancelled');
exception when duplicate_object then null; end $$;

do $$ begin
  create type app.pay_method as enum ('balance','cash','wechat','alipay');
exception when duplicate_object then null; end $$;

do $$ begin
  create type app.bind_role as enum ('admin','member');
exception when duplicate_object then null; end $$;

do $$ begin
  create type app.member_status as enum ('active','inactive','suspended','deleted');
exception when duplicate_object then null; end $$;

do $$ begin
  create type app.card_status as enum ('active','inactive','lost','expired');
exception when duplicate_object then null; end $$;

create sequence if not exists app.seq_member_no      start 1;
create sequence if not exists app.seq_personal_no    start 1;
create sequence if not exists app.seq_enterprise_no  start 1;
create sequence if not exists app.seq_tx_no          start 1;

-----------------------
-- 2) Security helpers (sec)
-----------------------
create or replace function sec.fixed_search_path()
returns void language plpgsql as $$
begin
  -- lock search_path for SECURITY DEFINER functions
  perform set_config('search_path', 'app, audit, public', true);
end $$;

-- derive an advisory lock key from uuid (first 64 bits)
create or replace function sec.card_lock_key(p_card uuid)
returns bigint language sql immutable as $$
  select ('x'||substr(replace(cast(p_card as text),'-',''),1,16))::bit(64)::bigint
$$;

-----------------------
-- 3) Common utilities (app)
-----------------------
create or replace function app.now_utc()
returns timestamptz language sql stable as $$ select now() at time zone 'utc' $$;

create or replace function app.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := app.now_utc(); return new; end $$;

create or replace function app.gen_member_no() returns text language plpgsql as $$
begin return 'M'||lpad(nextval('app.seq_member_no')::text,8,'0'); end $$;

create or replace function app.gen_personal_no() returns text language plpgsql as $$
begin return 'VIP'||lpad(nextval('app.seq_personal_no')::text,8,'0'); end $$;

create or replace function app.gen_enterprise_no() returns text language plpgsql as $$
begin return 'ENT'||lpad(nextval('app.seq_enterprise_no')::text,8,'0'); end $$;

create or replace function app.gen_tx_no(p_type app.tx_type) returns text language plpgsql as $$
begin
  if p_type='payment'  then return 'ZF'||lpad(nextval('app.seq_tx_no')::text,6,'0'); end if;
  if p_type='refund'   then return 'TQ'||lpad(nextval('app.seq_tx_no')::text,6,'0'); end if;
  if p_type='recharge' then return 'CZ'||lpad(nextval('app.seq_tx_no')::text,6,'0'); end if;
  return 'ZF'||lpad(nextval('app.seq_tx_no')::text,6,'0');
end $$;

-----------------------
-- 4) Members / Merchants / Levels
-----------------------
create table if not exists app.member_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  member_no text unique not null default app.gen_member_no(),
  name text, phone text, email text, wechat_id text,
  status app.member_status default 'active',
  created_at timestamptz default app.now_utc(),
  updated_at timestamptz default app.now_utc()
);
drop trigger if exists trg_mp_u on app.member_profiles;
create trigger trg_mp_u before update on app.member_profiles
  for each row execute function app.set_updated_at();

create table if not exists app.merchants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  code text unique not null,
  active boolean default true,
  created_at timestamptz default app.now_utc(),
  updated_at timestamptz default app.now_utc()
);
drop trigger if exists trg_mer_u on app.merchants;
create trigger trg_mer_u before update on app.merchants
  for each row execute function app.set_updated_at();

create table if not exists app.merchant_users (
  merchant_id uuid not null references app.merchants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text check (role in ('owner','cashier','admin')) default 'cashier',
  created_at timestamptz default app.now_utc(),
  primary key (merchant_id, user_id)
);

create table if not exists app.membership_levels (
  level int primary key,
  min_points int not null,
  max_points int, -- null = no upper bound
  discount numeric(4,3) not null check (discount>0 and discount<=1),
  is_active boolean default true,
  created_at timestamptz default app.now_utc(),
  updated_at timestamptz default app.now_utc()
);
drop trigger if exists trg_lvl_u on app.membership_levels;
create trigger trg_lvl_u before update on app.membership_levels
  for each row execute function app.set_updated_at();

-- prevent overlapping ranges
create or replace function app.levels_no_overlap()
returns trigger language plpgsql as $$
declare overlap boolean;
begin
  select exists (
    select 1 from app.membership_levels m
    where m.level <> coalesce(new.level,-1)
      and m.is_active and new.is_active
      and greatest(coalesce(m.min_points,0), coalesce(new.min_points,0))
          <= least(coalesce(m.max_points, 2147483647), coalesce(new.max_points,2147483647))
  ) into overlap;
  if overlap then
    raise exception using errcode='P0001', message='LEVEL_OVERLAP: membership level ranges overlap';
  end if;
  return new;
end $$;
drop trigger if exists trg_lvl_overlap on app.membership_levels;
create trigger trg_lvl_overlap
  before insert or update on app.membership_levels
  for each row execute function app.levels_no_overlap();

insert into app.membership_levels(level,min_points,max_points,discount) values
 (0,0,4999,1.000),
 (1,5000,9999,0.950),
 (2,10000,14999,0.900),
 (3,15000,19999,0.850),
 (4,20000,null,0.800)
on conflict(level) do update
  set min_points=excluded.min_points, max_points=excluded.max_points, discount=excluded.discount;

-----------------------
-- 5) Cards (QR hashed); bindings
-----------------------
-- Optional card types abstraction
create table if not exists app.card_types (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,              -- 'PERSONAL','ENTERPRISE'
  name text not null,
  use_levels boolean not null default false,
  has_fixed_discount boolean not null default false,
  default_fixed_discount numeric(4,3) default 1.000 check (default_fixed_discount>0 and default_fixed_discount<=1),
  require_bind_password boolean not null default false,
  allow_multiple_users boolean not null default false,
  created_at timestamptz default app.now_utc(),
  updated_at timestamptz default app.now_utc()
);
drop trigger if exists trg_cardtypes_u on app.card_types;
create trigger trg_cardtypes_u before update on app.card_types
  for each row execute function app.set_updated_at();

insert into app.card_types(code,name,use_levels,has_fixed_discount,default_fixed_discount,require_bind_password,allow_multiple_users)
values
('PERSONAL','个人卡', true,  false, null, false, false),
('ENTERPRISE','企业卡', false, true,  1.000, true,  true)
on conflict(code) do nothing;

create table if not exists app.personal_cards (
  id uuid primary key default gen_random_uuid(),
  card_no text unique not null default app.gen_personal_no(),
  member_id uuid not null references app.member_profiles(id) on delete cascade,
  balance numeric(12,2) not null default 0,
  points int not null default 0,
  level int not null default 0,
  discount numeric(4,3) not null default 1.000,
  qr_code_hash text,
  qr_code_updated_at timestamptz,
  expires_at timestamptz,
  status app.card_status default 'active',
  card_type_id uuid references app.card_types(id),
  created_at timestamptz default app.now_utc(),
  updated_at timestamptz default app.now_utc()
);
create index if not exists idx_pc_member on app.personal_cards(member_id);
drop trigger if exists trg_pc_u on app.personal_cards;
create trigger trg_pc_u before update on app.personal_cards
  for each row execute function app.set_updated_at();

create table if not exists app.enterprise_cards (
  id uuid primary key default gen_random_uuid(),
  card_no text unique not null default app.gen_enterprise_no(),
  company_name text not null,
  password_hash text not null, -- bcrypt
  fixed_discount numeric(4,3) not null default 1.000,
  balance numeric(12,2) not null default 0,
  qr_code_hash text,
  qr_code_updated_at timestamptz,
  expires_at timestamptz,
  status app.card_status default 'active',
  card_type_id uuid references app.card_types(id),
  created_at timestamptz default app.now_utc(),
  updated_at timestamptz default app.now_utc()
);
drop trigger if exists trg_ec_u on app.enterprise_cards;
create trigger trg_ec_u before update on app.enterprise_cards
  for each row execute function app.set_updated_at();

create table if not exists app.enterprise_card_bindings (
  enterprise_card_id uuid not null references app.enterprise_cards(id) on delete cascade,
  member_id uuid not null references app.member_profiles(id) on delete cascade,
  role app.bind_role not null default 'member',
  created_at timestamptz default app.now_utc(),
  created_by uuid references app.member_profiles(id),
  primary key (enterprise_card_id, member_id)
);
create index if not exists idx_ecb_member on app.enterprise_card_bindings(member_id);
create index if not exists idx_ecb_admin on app.enterprise_card_bindings(enterprise_card_id) where role='admin';

-----------------------
-- 6) Transactions (Monthly partitions, no global PK/UNIQUE)
-----------------------
create table if not exists app.transactions (
  id uuid not null,                -- per-partition unique index will enforce uniqueness
  tx_no text not null,             -- per-partition unique index
  card_type app.card_type not null,
  card_id uuid not null,
  merchant_id uuid references app.merchants(id),
  tx_type app.tx_type not null,
  raw_amount numeric(12,2) not null check (raw_amount>0),
  discount_applied numeric(4,3) not null check (discount_applied>0 and discount_applied<=1),
  final_amount numeric(12,2) not null check (final_amount>=0),
  points_earned int not null default 0,
  status app.tx_status not null default 'processing',
  tag jsonb default '{}'::jsonb,
  reason text,
  payment_method app.pay_method default 'balance',
  external_order_id text,
  idempotency_key text,
  processed_by_user_id uuid references auth.users(id),
  created_at timestamptz not null default app.now_utc()
) partition by range (created_at);

-- create current month partition + per-partition unique indexes
do $$
declare
  p text := to_char(date_trunc('month', now()), '"y"YYYY"m"MM');
  s timestamptz := date_trunc('month', now());
  e timestamptz := (date_trunc('month', now()) + interval '1 month');
begin
  execute format('create table if not exists app.transactions_%s partition of app.transactions for values from (%L) to (%L);', p, s, e);

  -- Uniques inside partition
  execute format('create unique index if not exists uq_tx_%s_id     on app.transactions_%s(id);', p, p);
  execute format('create unique index if not exists uq_tx_%s_no     on app.transactions_%s(tx_no);', p, p);
  execute format('create unique index if not exists uq_tx_%s_idem   on app.transactions_%s(idempotency_key) where idempotency_key is not null;', p, p);
  execute format('create unique index if not exists uq_tx_%s_ext    on app.transactions_%s(merchant_id, external_order_id) where external_order_id is not null;', p, p);

  -- Common lookups
  execute format('create index if not exists idx_tx_%s_card_time     on app.transactions_%s(card_id, created_at desc);', p, p);
  execute format('create index if not exists idx_tx_%s_merchant_time on app.transactions_%s(merchant_id, created_at desc);', p, p);
  execute format('create index if not exists idx_tx_%s_status        on app.transactions_%s(status);', p, p);
end $$;

-----------------------
-- 7) Global registries for cross-month uniqueness
-----------------------
create table if not exists app.tx_registry (
  tx_no text primary key,
  tx_id uuid unique not null,
  created_at timestamptz not null default app.now_utc()
);

create table if not exists app.idempotency_registry (
  idempotency_key text primary key,
  tx_id uuid unique not null,
  created_at timestamptz not null default app.now_utc()
);

create table if not exists app.merchant_order_registry (
  merchant_id uuid references app.merchants(id),
  external_order_id text not null,
  tx_id uuid unique not null,
  created_at timestamptz not null default app.now_utc(),
  unique (merchant_id, external_order_id)
);

-----------------------
-- 8) Audit
-----------------------
create table if not exists audit.event_log (
  id bigserial primary key,
  happened_at timestamptz not null default app.now_utc(),
  actor_user_id uuid,
  action text not null,          -- 'PAYMENT','REFUND','RECHARGE','BIND','UNBIND','AUTO_ISSUE','CRON_EXPIRE'
  object_type text not null,     -- 'personal_card','enterprise_card','transaction','system'
  object_id uuid,
  context jsonb not null default '{}'::jsonb
);
revoke all on audit.event_log from public;

create or replace function audit.log(p_action text, p_object_type text, p_object_id uuid, p_ctx jsonb)
returns void language sql as $$
  insert into audit.event_log(actor_user_id, action, object_type, object_id, context)
  values (auth.uid(), p_action, p_object_type, p_object_id, coalesce(p_ctx,'{}'::jsonb));
$$;

-----------------------
-- 9) Business helpers & triggers
-----------------------
create or replace function app.compute_personal_discount(p_points int)
returns numeric(4,3) language sql stable as $$
  select coalesce((
    select discount from app.membership_levels
    where is_active
      and p_points >= min_points
      and (max_points is null or p_points <= max_points)
    order by level desc
    limit 1
  ), 1.000)
$$;

-- auto issue personal card after member created
create or replace function app.after_insert_member_create_card()
returns trigger language plpgsql as $$
begin
  perform sec.fixed_search_path();
  insert into app.personal_cards(member_id, level, discount, points, card_type_id)
  values (new.id, 0, app.compute_personal_discount(0), 0,
         (select id from app.card_types where code='PERSONAL' limit 1));
  perform audit.log('AUTO_ISSUE','personal_card', new.id, jsonb_build_object('member_no', new.member_no));
  return new;
end $$;
drop trigger if exists trg_member_auto_card on app.member_profiles;
create trigger trg_member_auto_card
after insert on app.member_profiles
for each row execute function app.after_insert_member_create_card();

-----------------------
-- 10) RPCs (SECURITY DEFINER)
-----------------------

-- 10.1 Rotate QR (ownership/admin checks)
create or replace function app.rotate_card_qr(p_card_id uuid, p_card_type app.card_type)
returns table(qr_plain text, qr_expires_at timestamptz)
language plpgsql security definer as $$
declare v_plain text := encode(gen_random_bytes(32),'base64');
        v_ok boolean := false;
begin
  perform sec.fixed_search_path();

  if p_card_type='personal' then
    select exists(
      select 1 from app.personal_cards pc
      where pc.id=p_card_id and pc.member_id=auth.uid() and pc.status='active'
    ) into v_ok;
    if not v_ok then raise exception 'NOT_CARD_OWNER_OR_INACTIVE'; end if;

    update app.personal_cards
       set qr_code_hash = crypt(v_plain, gen_salt('bf')),
           qr_code_updated_at = app.now_utc()
     where id = p_card_id;

  else
    select exists(
      select 1 from app.enterprise_card_bindings b
      join app.enterprise_cards ec on ec.id=b.enterprise_card_id
      where b.enterprise_card_id=p_card_id and b.member_id=auth.uid() and b.role='admin' and ec.status='active'
    ) into v_ok;
    if not v_ok then raise exception 'ONLY_ENTERPRISE_ADMIN_CAN_ROTATE_QR_OR_INACTIVE'; end if;

    update app.enterprise_cards
       set qr_code_hash = crypt(v_plain, gen_salt('bf')),
           qr_code_updated_at = app.now_utc()
     where id = p_card_id;
  end if;

  return query select v_plain, app.now_utc() + interval '15 minutes';
end $$;

-- 10.2 Enterprise: set initial admin
create or replace function app.enterprise_set_initial_admin(p_card_no text, p_member_no text)
returns boolean language plpgsql security definer as $$
declare v_card app.enterprise_cards%rowtype; v_me app.member_profiles%rowtype;
begin
  perform sec.fixed_search_path();
  select * into v_card from app.enterprise_cards where card_no=p_card_no;
  if not found then raise exception 'CARD_NOT_FOUND'; end if;
  select * into v_me from app.member_profiles where member_no=p_member_no;
  if not found then raise exception 'MEMBER_NOT_FOUND'; end if;
  insert into app.enterprise_card_bindings(enterprise_card_id, member_id, role, created_by)
  values (v_card.id, v_me.id, 'admin', v_me.id)
  on conflict (enterprise_card_id, member_id) do update set role='admin';
  perform audit.log('SET_ENTERPRISE_ADMIN','enterprise_card', v_card.id, jsonb_build_object('member_no',p_member_no));
  return true;
end $$;

-- 10.3 Enterprise: admin add member (with card password)
create or replace function app.enterprise_add_member(p_card_no text, p_member_no text, p_card_password text)
returns boolean language plpgsql security definer as $$
declare v_card app.enterprise_cards%rowtype; v_me app.member_profiles%rowtype; v_is_admin boolean;
begin
  perform sec.fixed_search_path();
  select * into v_card from app.enterprise_cards where card_no=p_card_no and status='active';
  if not found then raise exception 'CARD_NOT_FOUND_OR_INACTIVE'; end if;

  select exists(
    select 1 from app.enterprise_card_bindings b
    where b.enterprise_card_id=v_card.id and b.member_id=auth.uid() and b.role='admin'
  ) into v_is_admin;
  if not v_is_admin then raise exception 'ONLY_ADMIN_BIND_ALLOWED'; end if;

  if not (v_card.password_hash = crypt(p_card_password, v_card.password_hash)) then
    raise exception 'INVALID_CARD_PASSWORD'; end if;

  select * into v_me from app.member_profiles where member_no=p_member_no and status='active';
  if not found then raise exception 'MEMBER_NOT_FOUND_OR_INACTIVE'; end if;

  insert into app.enterprise_card_bindings(enterprise_card_id, member_id, role, created_by)
  values (v_card.id, v_me.id, 'member', auth.uid())
  on conflict (enterprise_card_id, member_id) do update set role='member';

  perform audit.log('BIND_MEMBER','enterprise_card', v_card.id, jsonb_build_object('member_id',v_me.id));
  return true;
end $$;

-- 10.4 Enterprise: remove member (self or admin)
create or replace function app.enterprise_remove_member(p_card_no text, p_member_no text)
returns boolean language plpgsql security definer as $$
declare v_card app.enterprise_cards%rowtype; v_me app.member_profiles%rowtype; v_is_admin boolean;
begin
  perform sec.fixed_search_path();
  select * into v_card from app.enterprise_cards where card_no=p_card_no; if not found then raise exception 'CARD_NOT_FOUND'; end if;
  select * into v_me from app.member_profiles where member_no=p_member_no; if not found then raise exception 'MEMBER_NOT_FOUND'; end if;

  select exists(
    select 1 from app.enterprise_card_bindings where enterprise_card_id=v_card.id and member_id=auth.uid() and role='admin'
  ) into v_is_admin;

  if not (v_is_admin or v_me.id=auth.uid()) then raise exception 'UNBIND_NOT_ALLOWED'; end if;

  delete from app.enterprise_card_bindings where enterprise_card_id=v_card.id and member_id=v_me.id;
  perform audit.log('UNBIND_MEMBER','enterprise_card', v_card.id, jsonb_build_object('member_id',v_me.id));
  return true;
end $$;

-- 10.5 Merchant: charge by QR (locks + registries + partition insert)
create or replace function app.merchant_charge_by_qr(
  p_merchant_code text,
  p_qr_plain text,
  p_raw_price numeric,
  p_reason text default null,
  p_tag jsonb default '{}'::jsonb,
  p_idempotency_key text default null,
  p_external_order_id text default null
) returns table (tx_id uuid, tx_no text, card_type app.card_type, card_id uuid, final_amount numeric, discount numeric)
language plpgsql security definer as $$
declare
  v_merch app.merchants%rowtype;
  v_is_merch_user boolean;
  v_card_type app.card_type;
  v_pc app.personal_cards%rowtype;
  v_ec app.enterprise_cards%rowtype;
  v_disc numeric(4,3) := 1.000;
  v_final numeric(12,2);
  v_tx_id uuid := gen_random_uuid();
  v_tx_no text;
  v_lock_key bigint;
  v_points int;
begin
  perform sec.fixed_search_path();

  if p_raw_price is null or p_raw_price<=0 then raise exception 'INVALID_PRICE'; end if;
  if p_qr_plain is null or length(p_qr_plain)<16 then raise exception 'INVALID_QR'; end if;

  select * into v_merch from app.merchants where code=p_merchant_code and active=true;
  if not found then raise exception 'MERCHANT_NOT_FOUND_OR_INACTIVE'; end if;

  select exists(select 1 from app.merchant_users where merchant_id=v_merch.id and user_id=auth.uid())
    into v_is_merch_user;
  if not v_is_merch_user then raise exception 'NOT_MERCHANT_USER'; end if;

  -- match personal then enterprise (15min window; hashed)
  select * into v_pc
  from app.personal_cards
  where status='active'
    and qr_code_updated_at >= app.now_utc() - interval '15 minutes'
    and qr_code_hash is not null
    and qr_code_hash = crypt(p_qr_plain, qr_code_hash)
  for update;

  if found then
    v_card_type := 'personal';
    v_lock_key := sec.card_lock_key(v_pc.id);
    perform pg_advisory_xact_lock(v_lock_key);
  else
    select * into v_ec
    from app.enterprise_cards
    where status='active'
      and qr_code_updated_at >= app.now_utc() - interval '15 minutes'
      and qr_code_hash is not null
      and qr_code_hash = crypt(p_qr_plain, qr_code_hash)
    for update;
    if not found then raise exception 'QR_EXPIRED_OR_INVALID'; end if;
    v_card_type := 'enterprise';
    v_lock_key := sec.card_lock_key(v_ec.id);
    perform pg_advisory_xact_lock(v_lock_key);
  end if;

  -- idempotency registry (global, small)
  if p_idempotency_key is not null then
    begin
      insert into app.idempotency_registry(idempotency_key, tx_id) values (p_idempotency_key, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_type, t.card_id, t.final_amount, t.discount_applied
        from app.idempotency_registry ir
        join app.transactions t on t.id = ir.tx_id
        where ir.idempotency_key = p_idempotency_key and t.status='completed'
        limit 1;
      return;
    end;
  end if;

  -- merchant+external order registry (optional)
  if p_external_order_id is not null then
    begin
      insert into app.merchant_order_registry(merchant_id, external_order_id, tx_id)
      values (v_merch.id, p_external_order_id, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_type, t.card_id, t.final_amount, t.discount_applied
        from app.merchant_order_registry mo
        join app.transactions t on t.id = mo.tx_id
        where mo.merchant_id=v_merch.id and mo.external_order_id=p_external_order_id and t.status='completed'
        limit 1;
      return;
    end;
  end if;

  -- compute discount & balances
  if v_card_type='personal' then
    v_disc  := app.compute_personal_discount(v_pc.points);
    v_final := round(p_raw_price * v_disc, 2);
    if v_pc.balance < v_final then raise exception 'INSUFFICIENT_BALANCE'; end if;

    v_points := floor(p_raw_price)::int;
    v_tx_no := app.gen_tx_no('payment');
    insert into app.tx_registry(tx_no, tx_id) values (v_tx_no, v_tx_id)
    on conflict (tx_no) do nothing;

    insert into app.transactions(
           id, tx_no, card_type, card_id, merchant_id, tx_type,
           raw_amount, discount_applied, final_amount, points_earned,
           status, tag, reason, payment_method, idempotency_key, external_order_id, processed_by_user_id)
    values (v_tx_id, v_tx_no, 'personal', v_pc.id, v_merch.id, 'payment',
           p_raw_price, v_disc, v_final, v_points,
           'processing', coalesce(p_tag,'{}'::jsonb), p_reason, 'balance', p_idempotency_key, p_external_order_id, auth.uid());

    update app.personal_cards
       set balance = balance - v_final,
           points  = points + v_points,
           level   = (select level from app.membership_levels
                      where is_active and points >= min_points and (max_points is null or points <= max_points)
                      order by level desc limit 1),
           discount = app.compute_personal_discount(points)
     where id = v_pc.id;

    insert into app.point_ledger(id, personal_card_id, tx_id, change, balance_before, balance_after, reason, created_at, member_id, card_id)
    values (gen_random_uuid(), v_pc.id, v_tx_id, v_points,
            v_pc.points, (select points from app.personal_cards where id=v_pc.id),
            'payment_earn', app.now_utc(), v_pc.member_id, v_pc.id);

  else
    v_disc  := v_ec.fixed_discount;
    v_final := round(p_raw_price * v_disc, 2);
    if v_ec.balance < v_final then raise exception 'INSUFFICIENT_BALANCE'; end if;

    v_tx_no := app.gen_tx_no('payment');
    insert into app.tx_registry(tx_no, tx_id) values (v_tx_no, v_tx_id)
    on conflict (tx_no) do nothing;

    insert into app.transactions(
           id, tx_no, card_type, card_id, merchant_id, tx_type,
           raw_amount, discount_applied, final_amount, points_earned,
           status, tag, reason, payment_method, idempotency_key, external_order_id, processed_by_user_id)
    values (v_tx_id, v_tx_no, 'enterprise', v_ec.id, v_merch.id, 'payment',
           p_raw_price, v_disc, v_final, 0,
           'processing', coalesce(p_tag,'{}'::jsonb), p_reason, 'balance', p_idempotency_key, p_external_order_id, auth.uid());

    update app.enterprise_cards set balance = balance - v_final where id = v_ec.id;
  end if;

  update app.transactions set status='completed' where id = v_tx_id;
  perform audit.log('PAYMENT','transaction', v_tx_id, jsonb_build_object('merchant',v_merch.code,'final',v_final));

  return query select v_tx_id, v_tx_no, v_card_type,
                       case when v_card_type='personal' then v_pc.id else v_ec.id end,
                       v_final, v_disc;
end $$;

-- 10.6 Merchant: refund (partial/multiple)
create or replace function app.merchant_refund_tx(
  p_merchant_code text,
  p_original_tx_no text,
  p_refund_amount numeric,
  p_reason text default null,
  p_tag jsonb default '{}'::jsonb
) returns table (refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)
language plpgsql security definer as $$
declare
  v_merch app.merchants%rowtype;
  v_orig app.transactions%rowtype;
  v_ref_left numeric(12,2);
  v_ref_tx_id uuid := gen_random_uuid();
  v_ref_tx_no text;
begin
  perform sec.fixed_search_path();

  if p_refund_amount is null or p_refund_amount<=0 then raise exception 'INVALID_REFUND_AMOUNT'; end if;

  select * into v_merch from app.merchants where code=p_merchant_code and active=true;
  if not found then raise exception 'MERCHANT_NOT_FOUND_OR_INACTIVE'; end if;

  select * into v_orig from app.transactions where tx_no=p_original_tx_no and merchant_id=v_merch.id;
  if not found then raise exception 'ORIGINAL_TX_NOT_FOUND'; end if;
  if v_orig.tx_type<>'payment' or v_orig.status<>'completed' then raise exception 'ONLY_COMPLETED_PAYMENT_REFUNDABLE'; end if;

  select v_orig.final_amount - coalesce(sum(final_amount),0)
    into v_ref_left
  from app.transactions
  where tx_type='refund' and status in ('processing','completed')
    and card_id=v_orig.card_id and card_type=v_orig.card_type
    and reason=v_orig.tx_no;
  if v_ref_left is null then v_ref_left := v_orig.final_amount; end if;
  if p_refund_amount > v_ref_left then raise exception 'REFUND_EXCEEDS_REMAINING'; end if;

  -- lock card
  if v_orig.card_type='personal' then
    perform 1 from app.personal_cards where id=v_orig.card_id for update;
    perform pg_advisory_xact_lock(sec.card_lock_key(v_orig.card_id));
  else
    perform 1 from app.enterprise_cards where id=v_orig.card_id for update;
    perform pg_advisory_xact_lock(sec.card_lock_key(v_orig.card_id));
  end if;

  v_ref_tx_no := app.gen_tx_no('refund');
  insert into app.tx_registry(tx_no, tx_id) values (v_ref_tx_no, v_ref_tx_id)
  on conflict (tx_no) do nothing;

  insert into app.transactions(id, tx_no, card_type, card_id, merchant_id, tx_type,
         raw_amount, discount_applied, final_amount, points_earned,
         status, tag, reason, payment_method, processed_by_user_id)
  values (v_ref_tx_id, v_ref_tx_no, v_orig.card_type, v_orig.card_id, v_merch.id, 'refund',
         p_refund_amount, 1.000, p_refund_amount, 0,
         'processing', coalesce(p_tag,'{}'::jsonb), v_orig.tx_no, v_orig.payment_method, auth.uid());

  if v_orig.card_type='personal' then
    update app.personal_cards set balance = balance + p_refund_amount where id=v_orig.card_id;
  else
    update app.enterprise_cards set balance = balance + p_refund_amount where id=v_orig.card_id;
  end if;

  update app.transactions set status='completed' where id=v_ref_tx_id;
  perform audit.log('REFUND','transaction', v_ref_tx_id, jsonb_build_object('merchant',v_merch.code,'amount',p_refund_amount));

  return query select v_ref_tx_id, v_ref_tx_no, p_refund_amount;
end $$;

-- 10.7 Personal: self recharge
create or replace function app.user_recharge_personal_card(
  p_personal_card_id uuid,
  p_amount numeric,
  p_payment_method app.pay_method default 'wechat',
  p_reason text default null,
  p_tag jsonb default '{}'::jsonb,
  p_idempotency_key text default null,
  p_external_order_id text default null
) returns table (tx_id uuid, tx_no text, card_id uuid, amount numeric)
language plpgsql security definer as $$
declare v_pc app.personal_cards%rowtype; v_tx_id uuid := gen_random_uuid(); v_tx_no text;
begin
  perform sec.fixed_search_path();
  if p_amount is null or p_amount<=0 then raise exception 'INVALID_RECHARGE_AMOUNT'; end if;

  -- idempotency registry
  if p_idempotency_key is not null then
    begin
      insert into app.idempotency_registry(idempotency_key, tx_id) values (p_idempotency_key, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount
        from app.idempotency_registry ir
        join app.transactions t on t.id=ir.tx_id
        where ir.idempotency_key=p_idempotency_key and t.status='completed'
        limit 1;
      return;
    end;
  end if;

  select * into v_pc from app.personal_cards
   where id=p_personal_card_id and member_id=auth.uid() and status='active'
   for update;
  if not found then raise exception 'PERSONAL_CARD_NOT_FOUND_OR_NOT_OWNED'; end if;

  if p_external_order_id is not null then
    begin
      insert into app.merchant_order_registry(merchant_id, external_order_id, tx_id)
      values (null, p_external_order_id, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount
        from app.merchant_order_registry mo
        join app.transactions t on t.id=mo.tx_id
        where mo.merchant_id is null and mo.external_order_id=p_external_order_id and t.status='completed'
        limit 1;
      return;
    end;
  end if;

  v_tx_no := app.gen_tx_no('recharge');
  insert into app.tx_registry(tx_no, tx_id) values (v_tx_no, v_tx_id)
  on conflict (tx_no) do nothing;

  insert into app.transactions(id, tx_no, card_type, card_id, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned,
    status, tag, reason, payment_method, idempotency_key, external_order_id, processed_by_user_id)
  values (v_tx_id, v_tx_no, 'personal', v_pc.id, null, 'recharge',
    p_amount, 1.000, p_amount, 0,
    'processing', coalesce(p_tag,'{}'::jsonb), p_reason, p_payment_method,
    p_idempotency_key, p_external_order_id, auth.uid());

  update app.personal_cards set balance = balance + p_amount where id=v_pc.id;
  update app.transactions set status='completed' where id=v_tx_id;

  perform audit.log('RECHARGE','transaction', v_tx_id, jsonb_build_object('amount',p_amount,'method',p_payment_method));
  return query select v_tx_id, v_tx_no, v_pc.id, p_amount;
end $$;

-- 10.8 Enterprise: admin recharge
create or replace function app.user_recharge_enterprise_card_admin(
  p_enterprise_card_id uuid,
  p_amount numeric,
  p_payment_method app.pay_method default 'wechat',
  p_reason text default null,
  p_tag jsonb default '{}'::jsonb,
  p_idempotency_key text default null,
  p_external_order_id text default null
) returns table (tx_id uuid, tx_no text, card_id uuid, amount numeric)
language plpgsql security definer as $$
declare v_ec app.enterprise_cards%rowtype; v_is_admin boolean; v_tx_id uuid := gen_random_uuid(); v_tx_no text;
begin
  perform sec.fixed_search_path();
  if p_amount is null or p_amount<=0 then raise exception 'INVALID_RECHARGE_AMOUNT'; end if;

  select exists(
    select 1 from app.enterprise_card_bindings
    where enterprise_card_id=p_enterprise_card_id and member_id=auth.uid() and role='admin'
  ) into v_is_admin;
  if not v_is_admin then raise exception 'ONLY_ENTERPRISE_ADMIN_CAN_RECHARGE'; end if;

  -- idempotency registry
  if p_idempotency_key is not null then
    begin
      insert into app.idempotency_registry(idempotency_key, tx_id) values (p_idempotency_key, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount
        from app.idempotency_registry ir
        join app.transactions t on t.id=ir.tx_id
        where ir.idempotency_key=p_idempotency_key and t.status='completed'
        limit 1;
      return;
    end;
  end if;

  select * into v_ec from app.enterprise_cards
   where id=p_enterprise_card_id and status='active' for update;
  if not found then raise exception 'ENTERPRISE_CARD_NOT_FOUND_OR_INACTIVE'; end if;

  if p_external_order_id is not null then
    begin
      insert into app.merchant_order_registry(merchant_id, external_order_id, tx_id)
      values (null, p_external_order_id, v_tx_id);
    exception when unique_violation then
      return query
        select t.id, t.tx_no, t.card_id, t.final_amount
        from app.merchant_order_registry mo
        join app.transactions t on t.id=mo.tx_id
        where mo.merchant_id is null and mo.external_order_id=p_external_order_id and t.status='completed'
        limit 1;
      return;
    end;
  end if;

  v_tx_no := app.gen_tx_no('recharge');
  insert into app.tx_registry(tx_no, tx_id) values (v_tx_no, v_tx_id)
  on conflict (tx_no) do nothing;

  insert into app.transactions(id, tx_no, card_type, card_id, merchant_id, tx_type,
    raw_amount, discount_applied, final_amount, points_earned,
    status, tag, reason, payment_method, idempotency_key, external_order_id, processed_by_user_id)
  values (v_tx_id, v_tx_no, 'enterprise', v_ec.id, null, 'recharge',
    p_amount, 1.000, p_amount, 0,
    'processing', coalesce(p_tag,'{}'::jsonb), p_reason, p_payment_method,
    p_idempotency_key, p_external_order_id, auth.uid());

  update app.enterprise_cards set balance = balance + p_amount where id=v_ec.id;
  update app.transactions set status='completed' where id=v_tx_id;

  perform audit.log('RECHARGE','transaction', v_tx_id, jsonb_build_object('amount',p_amount,'method',p_payment_method));
  return query select v_tx_id, v_tx_no, v_ec.id, p_amount;
end $$;

-----------------------
-- 11) Views
-----------------------
create or replace view app.v_user_cards as
select
  pc.id as card_id,
  'personal'::app.card_type as card_type,
  pc.card_no,
  pc.balance,
  pc.level,
  pc.discount,
  pc.status,
  pc.created_at,
  pc.updated_at
from app.personal_cards pc
where pc.member_id = auth.uid()
union all
select
  ec.id as card_id,
  'enterprise'::app.card_type as card_type,
  ec.card_no,
  ec.balance,
  null::int as level,
  ec.fixed_discount as discount,
  ec.status,
  ec.created_at,
  ec.updated_at
from app.enterprise_cards ec
where exists (
  select 1 from app.enterprise_card_bindings b
  where b.enterprise_card_id = ec.id and b.member_id = auth.uid()
);

create or replace view app.v_usage_logs as
select
  t.id,
  t.created_at,
  t.tx_no,
  t.tx_type,
  t.card_type,
  t.card_id,
  t.merchant_id,
  t.raw_amount,
  t.discount_applied,
  t.final_amount,
  t.points_earned,
  t.status,
  t.reason,
  t.tag,
  t.payment_method
from app.transactions t
where
  (t.card_type='personal' and t.card_id in (select id from app.personal_cards where member_id=auth.uid()))
  or
  (t.card_type='enterprise' and exists (
    select 1 from app.enterprise_card_bindings b where b.enterprise_card_id=t.card_id and b.member_id=auth.uid()
  ))
  or
  (t.merchant_id in (select merchant_id from app.merchant_users where user_id=auth.uid()));

-----------------------
-- 12) Point ledger
-----------------------
create table if not exists app.point_ledger (
  id uuid primary key default gen_random_uuid(),
  personal_card_id uuid not null references app.personal_cards(id) on delete cascade,
  tx_id uuid, -- not FK due to partitioning; validated via RPC logic
  delta int not null,
  balance_after int not null,
  reason text,
  created_at timestamptz default app.now_utc()
);

-----------------------
-- 13) Expiry CRON
-----------------------
create or replace function app.cron_expire_cards()
returns int
language plpgsql
security definer
as $$
declare
  v_cnt int := 0;
  v_row int := 0;
begin
  perform sec.fixed_search_path();

  -- 个人卡过期
  update app.personal_cards
     set status='expired'
   where status='active'
     and expires_at is not null
     and expires_at < app.now_utc();
  get diagnostics v_row = ROW_COUNT;
  v_cnt := v_cnt + v_row;

  -- 企业卡过期
  update app.enterprise_cards
     set status='expired'
   where status='active'
     and expires_at is not null
     and expires_at < app.now_utc();
  get diagnostics v_row = ROW_COUNT;
  v_cnt := v_cnt + v_row;

  perform audit.log('CRON_EXPIRE','system', null, jsonb_build_object('affected', v_cnt));
  return v_cnt;
end $$;

-----------------------
-- 14) RLS
-----------------------
alter table app.member_profiles            enable row level security;
alter table app.personal_cards             enable row level security;
alter table app.enterprise_cards           enable row level security;
alter table app.enterprise_card_bindings   enable row level security;
alter table app.merchants                  enable row level security;
alter table app.merchant_users             enable row level security;
alter table app.membership_levels          enable row level security;
alter table app.transactions               enable row level security;
alter table app.point_ledger               enable row level security;

-- default deny
drop policy if exists deny_all_mp  on app.member_profiles;
create policy deny_all_mp  on app.member_profiles      for all using (false) with check (false);

drop policy if exists deny_all_pc  on app.personal_cards;
create policy deny_all_pc  on app.personal_cards       for all using (false) with check (false);

drop policy if exists deny_all_ec  on app.enterprise_cards;
create policy deny_all_ec  on app.enterprise_cards     for all using (false) with check (false);

drop policy if exists deny_all_ecb on app.enterprise_card_bindings;
create policy deny_all_ecb on app.enterprise_card_bindings for all using (false) with check (false);

drop policy if exists deny_all_mer on app.merchants;
create policy deny_all_mer on app.merchants            for all using (false) with check (false);

drop policy if exists deny_all_mu  on app.merchant_users;
create policy deny_all_mu  on app.merchant_users       for all using (false) with check (false);

drop policy if exists deny_all_lvl on app.membership_levels;
create policy deny_all_lvl on app.membership_levels    for all using (false) with check (false);

drop policy if exists deny_all_tx  on app.transactions;
create policy deny_all_tx  on app.transactions         for all using (false) with check (false);

drop policy if exists deny_all_pl  on app.point_ledger;
create policy deny_all_pl  on app.point_ledger         for all using (false) with check (false);

-- minimal READ policies
drop policy if exists mp_self_read on app.member_profiles;
create policy mp_self_read on app.member_profiles
  for select using (id=auth.uid());

drop policy if exists pc_owner_read on app.personal_cards;
create policy pc_owner_read on app.personal_cards
  for select using (member_id=auth.uid());

drop policy if exists ec_bound_read on app.enterprise_cards;
create policy ec_bound_read on app.enterprise_cards
  for select using (exists(
    select 1 from app.enterprise_card_bindings b
    where b.enterprise_card_id=app.enterprise_cards.id and b.member_id=auth.uid()
  ));

drop policy if exists ecb_member_or_admin_read on app.enterprise_card_bindings;
create policy ecb_member_or_admin_read on app.enterprise_card_bindings
  for select using (member_id=auth.uid() or exists(
    select 1 from app.enterprise_card_bindings b2
    where b2.enterprise_card_id=app.enterprise_card_bindings.enterprise_card_id and b2.member_id=auth.uid() and b2.role='admin'
  ));

drop policy if exists mer_user_read on app.merchants;
create policy mer_user_read on app.merchants
  for select using (exists(
    select 1 from app.merchant_users mu where mu.merchant_id=app.merchants.id and mu.user_id=auth.uid()
  ));

drop policy if exists mu_self_read on app.merchant_users;
create policy mu_self_read on app.merchant_users
  for select using (user_id=auth.uid());

drop policy if exists lvl_public_read on app.membership_levels;
create policy lvl_public_read on app.membership_levels
  for select using (is_active);

drop policy if exists tx_user_or_merchant_read on app.transactions;
create policy tx_user_or_merchant_read on app.transactions
  for select using (
    (card_type='personal' and card_id in (select id from app.personal_cards where member_id=auth.uid()))
    or
    (card_type='enterprise' and exists(
      select 1 from app.enterprise_card_bindings b where b.enterprise_card_id=app.transactions.card_id and b.member_id=auth.uid()
    ))
    or
    (merchant_id in (select merchant_id from app.merchant_users where user_id=auth.uid()))
  );

drop policy if exists pl_user_read on app.point_ledger;
create policy pl_user_read on app.point_ledger
  for select using (
    personal_card_id in (select id from app.personal_cards where member_id=auth.uid())
  );

-- ⚠️ No INSERT/UPDATE/DELETE policies for money-moving tables.
-- All writes occur only via SECURITY DEFINER RPCs above.
-- ============================================================================
-- END
-- ============================================================================
