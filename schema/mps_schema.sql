-- ============================================================================
-- Member Payment System (MPS) - SCHEMA ONLY (補強版) - PUBLIC SCHEMA
-- 包含 QR TABLES, external identities, stricter constraints, helpful indexes,
-- card_no auto-generation trigger, 並新增：
--   1. member_cards.binding_password_hash
--   2. transactions.refund index
--   3. settlement_status enum 增加 'paid'
--   4. audit.event_log 增加 object 索引
--   5. admin_users 表（管理員認證）
--   6. member_profiles.auth_user_id, password_hash（會員認證）
--   7. merchants.password_hash（商戶認證）
-- 修改：所有表移到 public schema 以提高安全性
-- ============================================================================

-- 0) DROP EXISTING TABLES (清除所有表格以重新建立)
DROP TABLE IF EXISTS audit.event_log CASCADE;
DROP TABLE IF EXISTS point_ledger CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS settlements CASCADE;
DROP TABLE IF EXISTS merchant_order_registry CASCADE;
DROP TABLE IF EXISTS idempotency_registry CASCADE;
DROP TABLE IF EXISTS tx_registry CASCADE;
DROP TABLE IF EXISTS card_qr_history CASCADE;
DROP TABLE IF EXISTS card_qr_state CASCADE;
DROP TABLE IF EXISTS merchant_users CASCADE;
DROP TABLE IF EXISTS admin_users CASCADE;
DROP TABLE IF EXISTS merchants CASCADE;
DROP TABLE IF EXISTS card_bindings CASCADE;
DROP TABLE IF EXISTS member_cards CASCADE;
DROP TABLE IF EXISTS membership_levels CASCADE;
DROP TABLE IF EXISTS member_external_identities CASCADE;
DROP TABLE IF EXISTS member_profiles CASCADE;

-- DROP SEQUENCES
DROP SEQUENCE IF EXISTS seq_member_no CASCADE;
DROP SEQUENCE IF EXISTS seq_card_no CASCADE;
DROP SEQUENCE IF EXISTS seq_tx_no CASCADE;

-- DROP TYPES
DROP TYPE IF EXISTS settlement_mode CASCADE;
DROP TYPE IF EXISTS settlement_status CASCADE;
DROP TYPE IF EXISTS member_status CASCADE;
DROP TYPE IF EXISTS bind_role CASCADE;
DROP TYPE IF EXISTS pay_method CASCADE;
DROP TYPE IF EXISTS tx_status CASCADE;
DROP TYPE IF EXISTS tx_type CASCADE;
DROP TYPE IF EXISTS card_status CASCADE;
DROP TYPE IF EXISTS card_type CASCADE;

-- SCHEMAS (drop & create)
DROP SCHEMA IF EXISTS audit CASCADE;
CREATE SCHEMA audit;

REVOKE ALL ON SCHEMA audit FROM public;

-- 1) ENUMS (在 public schema 中創建)
do $$ begin create type card_type as enum ('standard','prepaid','voucher','corporate'); exception when duplicate_object then null; end $$;
do $$ begin create type card_status as enum ('active','inactive','lost','expired','suspended','closed'); exception when duplicate_object then null; end $$;
do $$ begin create type tx_type as enum ('payment','refund','recharge'); exception when duplicate_object then null; end $$;
do $$ begin create type tx_status as enum ('processing','completed','failed','cancelled','refunded'); exception when duplicate_object then null; end $$;
do $$ begin create type pay_method as enum ('balance','cash','wechat','alipay'); exception when duplicate_object then null; end $$;
do $$ begin create type bind_role as enum ('owner','admin','member','viewer'); exception when duplicate_object then null; end $$;
do $$ begin create type member_status as enum ('active','inactive','suspended','deleted'); exception when duplicate_object then null; end $$;
do $$ begin create type settlement_status as enum ('pending','settled','failed','paid'); exception when duplicate_object then null; end $$;
do $$ begin create type settlement_mode as enum ('realtime','t_plus_1','monthly'); exception when duplicate_object then null; end $$;

comment on type bind_role is 'Card-level role: owner/admin/member/viewer';

-- 2) UTILITIES & SEQUENCES (在 public schema 中)
create or replace function now_utc() returns timestamptz language sql stable as $$
  select now() at time zone 'utc'
$$;

create or replace function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at := now_utc();
  return new;
end;
$$;

create sequence seq_member_no start 1;
create sequence seq_card_no   start 1;
create sequence seq_tx_no     start 1;

create or replace function gen_member_no() returns text language sql as $$
  select 'M' || lpad(nextval('seq_member_no')::text, 8, '0')
$$;

create or replace function gen_card_no(p_type card_type) returns text language plpgsql as $$
begin
  if p_type='standard'  then return 'STD' || lpad(nextval('seq_card_no')::text, 8, '0'); end if;
  if p_type='prepaid'   then return 'PPD' || lpad(nextval('seq_card_no')::text, 8, '0'); end if;
  if p_type='voucher'   then return 'VCH' || lpad(nextval('seq_card_no')::text, 8, '0'); end if;
  if p_type='corporate' then return 'COR' || lpad(nextval('seq_card_no')::text, 8, '0'); end if;
  return 'CARD' || lpad(nextval('seq_card_no')::text, 8, '0');
end;
$$;

create or replace function gen_tx_no(p_type tx_type) returns text language plpgsql as $$
begin
  if p_type='payment'  then return 'PAY' || lpad(nextval('seq_tx_no')::text, 10, '0'); end if;
  if p_type='refund'   then return 'REF' || lpad(nextval('seq_tx_no')::text, 10, '0'); end if;
  if p_type='recharge' then return 'RCG' || lpad(nextval('seq_tx_no')::text, 10, '0'); end if;
  return 'TX' || lpad(nextval('seq_tx_no')::text, 10, '0');
end;
$$;

-- 3) CORE TABLES (在 public schema 中)

-- 3.1 Member Profiles
create table member_profiles (
  id uuid primary key default gen_random_uuid(),
  member_no text unique not null default gen_member_no(),
  name text not null,
  phone text unique,
  email text unique,
  binding_user_org text,
  binding_org_id  text,
  role text not null default 'member',
  status member_status not null default 'active',
  owner_info jsonb not null default '{}'::jsonb,
  auth_user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  password_hash text,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc(),
  unique (binding_user_org, binding_org_id)
);

CREATE INDEX idx_member_profiles_auth_user ON member_profiles(auth_user_id);

COMMENT ON COLUMN member_profiles.auth_user_id IS '關聯的 Supabase Auth 用戶（可選）';
COMMENT ON COLUMN member_profiles.password_hash IS '會員登入密碼雜湊';

-- 3.1.b External Identities
create table member_external_identities (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references member_profiles(id) on delete cascade,
  provider text not null,
  external_id text not null,
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc(),
  unique (provider, external_id),
  unique (member_id, provider)
);

-- 3.2 Membership Levels
create table membership_levels (
  id uuid primary key default gen_random_uuid(),
  level int unique not null,
  name text not null,
  min_points int not null,
  max_points int,
  discount numeric(4,3) not null default 1.000,
  is_active boolean not null default true,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc()
);

-- 3.3 Member Cards
create table member_cards (
  id uuid primary key default gen_random_uuid(),
  card_no text unique not null,
  card_type card_type not null,
  owner_member_id uuid references member_profiles(id),
  name text,
  balance numeric(12,2) not null default 0,
  points int not null default 0,
  level int,
  discount numeric(4,3) not null default 1.000,
  fixed_discount numeric(4,3),
  binding_password_hash text,
  status card_status not null default 'active',
  expires_at timestamptz,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc(),
  check ( (card_type in ('standard','prepaid') and discount between 0.000 and 1.000)
       or (card_type in ('voucher','corporate')) )
);

-- card_no auto-fill
create or replace function before_insert_member_cards_fill_card_no()
returns trigger language plpgsql as $$
begin
  if new.card_no is null or length(new.card_no)=0 then
    new.card_no := gen_card_no(new.card_type);
  end if;
  return new;
end;
$$;

create trigger trg_member_cards_fill_card_no
before insert on member_cards
for each row execute function before_insert_member_cards_fill_card_no();

-- 3.4 Card Bindings
create table card_bindings (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references member_cards(id) on delete cascade,
  member_id uuid not null references member_profiles(id) on delete cascade,
  role bind_role not null default 'member',
  created_at timestamptz not null default now_utc(),
  unique (card_id, member_id)
);

-- 3.5 Merchants
create table merchants (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  name text not null,
  contact text,
  status text not null default 'active',
  password_hash text,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc()
);

COMMENT ON COLUMN merchants.password_hash IS '商戶登入密碼雜湊';
-- 3.6 Admin Users (管理員用戶表)
CREATE TABLE admin_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id uuid NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  role text NOT NULL DEFAULT 'admin', -- admin, super_admin
  permissions jsonb DEFAULT '[]'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now_utc(),
  updated_at timestamptz NOT NULL DEFAULT now_utc()
);

CREATE INDEX idx_admin_users_auth_user ON admin_users(auth_user_id);
CREATE INDEX idx_admin_users_active ON admin_users(is_active);

CREATE TRIGGER trg_admin_users_updated_at
BEFORE UPDATE ON admin_users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE admin_users IS '管理員用戶表，關聯 Supabase Auth';
COMMENT ON COLUMN admin_users.role IS 'admin: 一般管理員, super_admin: 超級管理員';


create table merchant_users (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references merchants(id) on delete cascade,
  auth_user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'staff',
  created_at timestamptz not null default now_utc(),
  unique (merchant_id, auth_user_id)
);

-- 4) QR TABLES
create table card_qr_state (
  card_id uuid primary key references member_cards(id) on delete cascade,
  token_hash text not null,
  expires_at timestamptz not null,
  updated_at timestamptz not null default now_utc()
);
create index idx_qr_state_expires on card_qr_state(expires_at);

create table card_qr_history (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references member_cards(id) on delete cascade,
  token_hash text not null,
  expires_at timestamptz not null,
  issued_by uuid,
  issued_at timestamptz not null default now_utc()
);
create index idx_qr_hist_card_time on card_qr_history(card_id, issued_at desc);

-- 5) REGISTRIES
create table tx_registry (
  tx_no text primary key,
  tx_id uuid unique not null,
  created_at timestamptz not null default now_utc()
);

create table idempotency_registry (
  idempotency_key text primary key,
  tx_id uuid unique not null,
  created_at timestamptz not null default now_utc()
);

create table merchant_order_registry (
  merchant_id uuid references merchants(id) on delete cascade,
  external_order_id text not null,
  tx_id uuid unique not null,
  created_at timestamptz not null default now_utc(),
  unique (merchant_id, external_order_id)
);

-- 6) TRANSACTIONS
create table transactions (
  id uuid primary key default gen_random_uuid(),
  tx_no text not null,
  tx_type tx_type not null,
  card_id uuid not null references member_cards(id),
  merchant_id uuid references merchants(id),
  raw_amount numeric(12,2) not null,
  discount_applied numeric(4,3) not null default 1.000,
  final_amount numeric(12,2) not null,
  points_earned int not null default 0,
  status tx_status not null default 'processing',
  reason text,
  payment_method pay_method default 'balance',
  external_order_id text,
  idempotency_key text,
  original_tx_id uuid references transactions(id),
  processed_by_user_id uuid references auth.users(id),
  tag jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc(),
  check (raw_amount > 0 and final_amount >= 0)
);
create unique index uq_tx_tx_no on transactions(tx_no);
create index idx_tx_card_time on transactions(card_id, created_at desc);
create index idx_tx_merchant_time on transactions(merchant_id, created_at desc);
create index idx_tx_status on transactions(status);
create index idx_tx_type_time on transactions(tx_type, created_at desc);
create index idx_tx_created_at on transactions(created_at);
create index idx_tx_tag_gin on transactions using gin(tag);
create index idx_tx_original on transactions(original_tx_id);

create table point_ledger (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references member_cards(id) on delete cascade,
  tx_id uuid references transactions(id),
  change int not null,
  balance_before int not null,
  balance_after int not null,
  reason text,
  created_at timestamptz not null default now_utc()
);

-- 7) SETTLEMENTS
create table settlements (
  id uuid primary key default gen_random_uuid(),
  merchant_id uuid not null references merchants(id) on delete cascade,
  mode settlement_mode not null default 'realtime',
  period_start timestamptz not null,
  period_end timestamptz not null,
  total_amount numeric(12,2) not null,
  total_tx_count int not null,
  status settlement_status not null default 'pending',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now_utc(),
  updated_at timestamptz not null default now_utc(),
  check (total_amount >= 0 and total_tx_count >= 0)
);

-- 8) AUDIT
create table audit.event_log (
  id bigserial primary key,
  happened_at timestamptz not null default now_utc(),
  actor_user_id uuid,
  action text not null,
  object_type text not null,
  object_id uuid,
  context jsonb not null default '{}'::jsonb
);
create index idx_event_object on audit.event_log(object_type, object_id);

-- 9) TRIGGERS (only updated_at maintenance)
create trigger trg_member_profiles_updated_at
before update on member_profiles
for each row execute function set_updated_at();

create trigger trg_member_ext_ids_updated_at
before update on member_external_identities
for each row execute function set_updated_at();

create trigger trg_membership_levels_updated_at
before update on membership_levels
for each row execute function set_updated_at();

create trigger trg_member_cards_updated_at
before update on member_cards
for each row execute function set_updated_at();

create trigger trg_merchants_updated_at
before update on merchants
for each row execute function set_updated_at();

create trigger trg_transactions_updated_at
before update on transactions
for each row execute function set_updated_at();

create trigger trg_settlements_updated_at
before update on settlements
for each row execute function set_updated_at();

-- 10) CONSTRAINT PATCHES
alter table member_cards
  add constraint ck_card_balance_nonneg check (balance >= 0),
  add constraint ck_card_points_nonneg check (points >= 0),
  add constraint ck_card_fixed_discount_range check (fixed_discount is null or (fixed_discount >= 0 and fixed_discount <= 1));

-- 11) HELPFUL INDEXES
create index idx_cards_status on member_cards(status);
create index idx_cards_owner_type on member_cards(owner_member_id, card_type);
create index idx_bindings_member on card_bindings(member_id);
create index idx_levels_level on membership_levels(level);

-- 12) SEED DATA
insert into membership_levels(level, name, min_points, max_points, discount, is_active) values
  (0, '普通會員', 0, 999, 1.000, true),
  (1, '銀卡會員', 1000, 4999, 0.950, true),
  (2, '金卡會員', 5000, 9999, 0.900, true),
  (3, '鑽石會員', 10000, null, 0.850, true)
on conflict do nothing;

-- ============================================================================
-- 13) ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- 啟用所有表的 RLS
ALTER TABLE member_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_external_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE membership_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE card_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchant_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE card_qr_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE card_qr_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE tx_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchant_order_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE point_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- ADMIN USERS - 管理員只能查看自己的資料
CREATE POLICY "Admins can view own profile" ON admin_users
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        auth_user_id = auth.uid()
    );

CREATE POLICY "Super admins can view all admins" ON admin_users
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        EXISTS (
            SELECT 1 FROM admin_users
            WHERE auth_user_id = auth.uid()
            AND role = 'super_admin'
            AND is_active = true
        )
    );

-- MEMBER PROFILES - 只能查看自己的資料
CREATE POLICY "Users can view own member profile" ON member_profiles
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        (binding_user_org = 'supabase' AND binding_org_id = auth.uid()::text)
    );

CREATE POLICY "Users can update own member profile" ON member_profiles
    FOR UPDATE USING (
        auth.uid() IS NOT NULL AND
        (binding_user_org = 'supabase' AND binding_org_id = auth.uid()::text)
    );

CREATE POLICY "Allow member registration" ON member_profiles
    FOR INSERT WITH CHECK (
        auth.uid() IS NOT NULL AND
        (binding_user_org = 'supabase' AND binding_org_id = auth.uid()::text)
    );

-- MEMBER EXTERNAL IDENTITIES
CREATE POLICY "Users can view own external identities" ON member_external_identities
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        member_id IN (
            SELECT id FROM member_profiles
            WHERE binding_user_org = 'supabase' AND binding_org_id = auth.uid()::text
        )
    );

-- MEMBERSHIP LEVELS - 公開資訊，所有人可讀
CREATE POLICY "Membership levels are public" ON membership_levels
    FOR SELECT USING (true);

-- MEMBER CARDS - 只能查看自己擁有或綁定的卡片
CREATE POLICY "Users can view own cards" ON member_cards
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND (
            owner_member_id IN (
                SELECT mp.id FROM member_profiles mp
                WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
            )
            OR member_cards.id IN (
                SELECT cb.card_id FROM card_bindings cb
                JOIN member_profiles mp ON mp.id = cb.member_id
                WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
            )
        )
    );

CREATE POLICY "Users can update own cards" ON member_cards
    FOR UPDATE USING (
        auth.uid() IS NOT NULL AND
        owner_member_id IN (
            SELECT mp.id FROM member_profiles mp
            WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
        )
    );

-- CARD BINDINGS - 只能查看自己相關的綁定
CREATE POLICY "Users can view own card bindings" ON card_bindings
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        member_id IN (
            SELECT mp.id FROM member_profiles mp
            WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
        )
    );

-- MERCHANTS - 商戶資訊部分公開（名稱等），詳細資訊需要權限
CREATE POLICY "Public merchant info" ON merchants
    FOR SELECT USING (true);

-- MERCHANT USERS - 只能查看自己的商戶關聯
CREATE POLICY "Users can view own merchant associations" ON merchant_users
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        auth_user_id = auth.uid()
    );

-- QR STATE - 只能查看自己卡片的 QR 狀態
CREATE POLICY "Users can view own card qr state" ON card_qr_state
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        card_id IN (
            SELECT mc.id FROM member_cards mc
            JOIN member_profiles mp ON mp.id = mc.owner_member_id
            WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
        )
    );

-- QR HISTORY - 只能查看自己卡片的 QR 歷史
CREATE POLICY "Users can view own card qr history" ON card_qr_history
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        card_id IN (
            SELECT mc.id FROM member_cards mc
            JOIN member_profiles mp ON mp.id = mc.owner_member_id
            WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
        )
    );

-- TRANSACTIONS - 只能查看自己相關的交易
CREATE POLICY "Users can view own transactions" ON transactions
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND (
            -- 自己卡片的交易
            card_id IN (
                SELECT mc.id FROM member_cards mc
                JOIN member_profiles mp ON mp.id = mc.owner_member_id
                WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
            )
            OR
            -- 自己商戶的交易
            merchant_id IN (
                SELECT mu.merchant_id FROM merchant_users mu
                WHERE mu.auth_user_id = auth.uid()
            )
        )
    );

-- POINT LEDGER - 只能查看自己卡片的積分記錄
CREATE POLICY "Users can view own point ledger" ON point_ledger
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        card_id IN (
            SELECT mc.id FROM member_cards mc
            JOIN member_profiles mp ON mp.id = mc.owner_member_id
            WHERE mp.binding_user_org = 'supabase' AND mp.binding_org_id = auth.uid()::text
        )
    );

-- SETTLEMENTS - 只能查看自己商戶的結算
CREATE POLICY "Merchants can view own settlements" ON settlements
    FOR SELECT USING (
        auth.uid() IS NOT NULL AND
        merchant_id IN (
            SELECT mu.merchant_id FROM merchant_users mu
            WHERE mu.auth_user_id = auth.uid()
        )
    );

-- TX REGISTRY, IDEMPOTENCY REGISTRY, MERCHANT ORDER REGISTRY
-- 這些表主要由 RPC 函數使用，限制直接訪問
CREATE POLICY "Restrict tx_registry access" ON tx_registry
    FOR SELECT USING (false);

CREATE POLICY "Restrict idempotency_registry access" ON idempotency_registry
    FOR SELECT USING (false);

CREATE POLICY "Restrict merchant_order_registry access" ON merchant_order_registry
    FOR SELECT USING (false);

-- End of SCHEMA ONLY (補強版) - PUBLIC SCHEMA WITH RLS
