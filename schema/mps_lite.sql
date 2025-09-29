-- ============================================================================
-- Member Payment System (MPS) - SCHEMA ONLY (WITH QR TABLES, NO RPCs)
-- Includes: external identities table, stricter constraints, helpful indexes,
--           and card_no auto-generation trigger.
-- This script DROPs and RECREATEs all objects in schemas app, audit.
-- Target: Supabase/PostgreSQL
-- ============================================================================

-- 0) SCHEMAS (drop & create)
drop schema if exists audit cascade;
drop schema if exists app cascade;
create schema app;
create schema audit;

revoke all on schema app   from public;
revoke all on schema audit from public;

-- 1) ENUMS
do $$ begin create type app.card_type as enum ('standard','prepaid','voucher','corporate'); exception when duplicate_object then null; end $$;
do $$ begin create type app.card_status as enum ('active','inactive','lost','expired','suspended','closed'); exception when duplicate_object then null; end $$;
do $$ begin create type app.tx_type as enum ('payment','refund','recharge'); exception when duplicate_object then null; end $$;
do $$ begin create type app.tx_status as enum ('processing','completed','failed','cancelled','refunded'); exception when duplicate_object then null; end $$;
do $$ begin create type app.pay_method as enum ('balance','cash','wechat','alipay'); exception when duplicate_object then null; end $$;
do $$ begin create type app.bind_role as enum ('owner','admin','member','viewer'); exception when duplicate_object then null; end $$;
do $$ begin create type app.member_status as enum ('active','inactive','suspended','deleted'); exception when duplicate_object then null; end $$;
do $$ begin create type app.settlement_status as enum ('pending','settled','failed'); exception when duplicate_object then null; end $$;
do $$ begin create type app.settlement_mode as enum ('realtime','t_plus_1','monthly'); exception when duplicate_object then null; end $$;

comment on type app.bind_role is 'Card-level role: owner/admin/member/viewer';

-- 2) UTILITIES & SEQUENCES
create or replace function app.now_utc() returns timestamptz language sql stable as $$
  select now() at time zone 'utc'
$$;

create or replace function app.set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at := app.now_utc();
  return new;
end;
$$;

create sequence app.seq_member_no start 1;
create sequence app.seq_card_no   start 1;
create sequence app.seq_tx_no     start 1;

create or replace function app.gen_member_no() returns text language sql as $$
  select 'M' || lpad(nextval('app.seq_member_no')::text, 8, '0')
$$;

create or replace function app.gen_card_no(p_type app.card_type) returns text language plpgsql as $$
begin
  if p_type='standard'  then return 'STD' || lpad(nextval('app.seq_card_no')::text, 8, '0'); end if;
  if p_type='prepaid'   then return 'PPD' || lpad(nextval('app.seq_card_no')::text, 8, '0'); end if;
  if p_type='voucher'   then return 'VCH' || lpad(nextval('app.seq_card_no')::text, 8, '0'); end if;
  if p_type='corporate' then return 'COR' || lpad(nextval('app.seq_card_no')::text, 8, '0'); end if;
  return 'CARD' || lpad(nextval('app.seq_card_no')::text, 8, '0');
end;
$$;

create or replace function app.gen_tx_no(p_type app.tx_type) returns text language plpgsql as $$
begin
  if p_type='payment'  then return 'PAY' || lpad(nextval('app.seq_tx_no')::text, 10, '0'); end if;
  if p_type='refund'   then return 'REF' || lpad(nextval('app.seq_tx_no')::text, 10, '0'); end if;
  if p_type='recharge' then return 'RCG' || lpad(nextval('app.seq_tx_no')::text, 10, '0'); end if;
  return 'TX' || lpad(nextval('app.seq_tx_no')::text, 10, '0');
end;
$$;

-- 3) CORE TABLES

-- 3.1 Member Profiles
create table app.member_profiles (
  id uuid primary key default gen_random_uuid(),
  member_no text unique not null default app.gen_member_no(),
  name text not null,
  phone text unique,
  email text unique,
  -- optional default binding for simple apps
  binding_user_org text,
  binding_org_id  text,
  role text not null default 'member',
  status app.member_status not null default 'active',
  owner_info jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc(),
  unique (binding_user_org, binding_org_id)
);

-- 3.1.b External Identities
create table app.member_external_identities (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references app.member_profiles(id) on delete cascade,
  provider text not null,
  external_id text not null,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc(),
  unique (provider, external_id),
  unique (member_id, provider)
);

-- 3.2 Membership Levels
create table app.membership_levels (
  id uuid primary key default gen_random_uuid(),
  level int unique not null,
  name text not null,
  min_points int not null,
  max_points int,
  discount numeric(4,3) not null default 1.000,
  is_active boolean not null default true,
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc()
);

-- 3.3 Member Cards
create table app.member_cards (
  id uuid primary key default gen_random_uuid(),
  card_no text unique not null,
  card_type app.card_type not null,
  owner_member_id uuid references app.member_profiles(id),
  name text,
  balance numeric(12,2) not null default 0,
  points int not null default 0,
  level int,
  discount numeric(4,3) not null default 1.000,
  fixed_discount numeric(4,3),
  status app.card_status not null default 'active',
  expires_at timestamptz,
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc(),
  check ( (card_type in ('standard','prepaid') and discount between 0.000 and 1.000)
       or (card_type in ('voucher','corporate')) )
);

-- card_no auto-fill
create or replace function app.before_insert_member_cards_fill_card_no()
returns trigger language plpgsql as $$
begin
  if new.card_no is null or length(new.card_no)=0 then
    new.card_no := app.gen_card_no(new.card_type);
  end if;
  return new;
end;
$$;

create trigger trg_member_cards_fill_card_no
before insert on app.member_cards
for each row execute function app.before_insert_member_cards_fill_card_no();

-- 3.4 Card Bindings
create table app.card_bindings (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references app.member_cards(id) on delete cascade,
  member_id uuid not null references app.member_profiles(id) on delete cascade,
  role app.bind_role not null default 'member',
  binding_password_hash text,
  created_at timestamptz not null default app.now_utc(),
  unique (card_id, member_id)
);

-- 3.5 Merchants
create table app.merchants (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  name text not null,
  contact text,
  status text not null default 'active',
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc()
);

create table app.merchant_users (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references app.merchants(id) on delete cascade,
  auth_user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'staff',
  created_at timestamptz not null default app.now_utc(),
  unique (merchant_id, auth_user_id)
);

-- 4) QR TABLES
create table app.card_qr_state (
  card_id uuid primary key references app.member_cards(id) on delete cascade,
  token_hash text not null,
  expires_at timestamptz not null,
  updated_at timestamptz not null default app.now_utc()
);
create index idx_qr_state_expires on app.card_qr_state(expires_at);

create table app.card_qr_history (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references app.member_cards(id) on delete cascade,
  token_hash text not null,
  expires_at timestamptz not null,
  issued_by uuid,
  issued_at timestamptz not null default app.now_utc()
);
create index idx_qr_hist_card_time on app.card_qr_history(card_id, issued_at desc);

-- 5) REGISTRIES
create table app.tx_registry (
  tx_no text primary key,
  tx_id uuid unique not null,
  created_at timestamptz not null default app.now_utc()
);

create table app.idempotency_registry (
  idempotency_key text primary key,
  tx_id uuid unique not null,
  created_at timestamptz not null default app.now_utc()
);

create table app.merchant_order_registry (
  merchant_id uuid references app.merchants(id) on delete cascade,
  external_order_id text not null,
  tx_id uuid unique not null,
  created_at timestamptz not null default app.now_utc(),
  unique (merchant_id, external_order_id)
);

-- 6) TRANSACTIONS
create table app.transactions (
  id uuid primary key default gen_random_uuid(),
  tx_no text not null,
  tx_type app.tx_type not null,
  card_id uuid not null references app.member_cards(id),
  merchant_id uuid references app.merchants(id),
  raw_amount numeric(12,2) not null,
  discount_applied numeric(4,3) not null default 1.000,
  final_amount numeric(12,2) not null,
  points_earned int not null default 0,
  status app.tx_status not null default 'processing',
  reason text,
  payment_method app.pay_method default 'balance',
  external_order_id text,
  idempotency_key text,
  original_tx_id uuid references app.transactions(id),
  processed_by_user_id uuid references auth.users(id),
  tag jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc(),
  check (raw_amount > 0 and final_amount >= 0)
);
create unique index uq_tx_tx_no on app.transactions(tx_no);
create index idx_tx_card_time on app.transactions(card_id, created_at desc);
create index idx_tx_merchant_time on app.transactions(merchant_id, created_at desc);
create index idx_tx_status on app.transactions(status);
create index idx_tx_type_time on app.transactions(tx_type, created_at desc);
create index idx_tx_created_at on app.transactions(created_at);
create index idx_tx_tag_gin on app.transactions using gin(tag);

create table app.point_ledger (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references app.member_cards(id) on delete cascade,
  tx_id uuid references app.transactions(id),
  change int not null,
  balance_before int not null,
  balance_after int not null,
  reason text,
  created_at timestamptz not null default app.now_utc()
);

-- 7) SETTLEMENTS
create table app.settlements (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references app.merchants(id) on delete cascade,
  mode app.settlement_mode not null default 'realtime',
  period_start timestamptz not null,
  period_end timestamptz not null,
  total_amount numeric(12,2) not null,
  total_tx_count int not null,
  status app.settlement_status not null default 'pending',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default app.now_utc(),
  updated_at timestamptz not null default app.now_utc(),
  check (total_amount >= 0 and total_tx_count >= 0)
);

-- 8) AUDIT
create table audit.event_log (
  id bigserial primary key,
  happened_at timestamptz not null default app.now_utc(),
  actor_user_id uuid,
  action text not null,
  object_type text not null,
  object_id uuid,
  context jsonb not null default '{}'::jsonb
);

-- 9) TRIGGERS (only updated_at maintenance)
create trigger trg_member_profiles_updated_at
before update on app.member_profiles
for each row execute function app.set_updated_at();

create trigger trg_member_ext_ids_updated_at
before update on app.member_external_identities
for each row execute function app.set_updated_at();

create trigger trg_membership_levels_updated_at
before update on app.membership_levels
for each row execute function app.set_updated_at();

create trigger trg_member_cards_updated_at
before update on app.member_cards
for each row execute function app.set_updated_at();

create trigger trg_merchants_updated_at
before update on app.merchants
for each row execute function app.set_updated_at();

create trigger trg_transactions_updated_at
before update on app.transactions
for each row execute function app.set_updated_at();

create trigger trg_settlements_updated_at
before update on app.settlements
for each row execute function app.set_updated_at();

-- 10) CONSTRAINT PATCHES
alter table app.member_cards
  add constraint ck_card_balance_nonneg check (balance >= 0),
  add constraint ck_card_points_nonneg check (points >= 0),
  add constraint ck_card_fixed_discount_range check (fixed_discount is null or (fixed_discount >= 0 and fixed_discount <= 1));

-- 11) HELPFUL INDEXES
create index idx_cards_status on app.member_cards(status);
create index idx_cards_owner_type on app.member_cards(owner_member_id, card_type);
create index idx_bindings_member on app.card_bindings(member_id);
create index idx_levels_level on app.membership_levels(level);

-- 12) SEED DATA
insert into app.membership_levels(level, name, min_points, max_points, discount, is_active) values
  (0, '普通會員', 0, 999, 1.000, true),
  (1, '銀卡會員', 1000, 4999, 0.950, true),
  (2, '金卡會員', 5000, 9999, 0.900, true),
  (3, '鑽石會員', 10000, null, 0.850, true)
on conflict do nothing;

-- End of SCHEMA ONLY
