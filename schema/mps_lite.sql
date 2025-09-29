-- mps_clean.sql
-- Member Payment System 基礎 Schema (無 RPC, 無 trigger)
-- 僅包含資料表、型別與必要 function

create schema if not exists app;
create schema if not exists audit;

-- Member Profiles
create table if not exists app.member_profiles (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  phone text,
  email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Member Cards
create table if not exists app.member_cards (
  id uuid primary key default gen_random_uuid(),
  member_id uuid references app.member_profiles(id) on delete cascade,
  card_type text not null,
  balance numeric(12,2) not null default 0,
  discount numeric(4,3) not null default 1.000,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Transactions
create table if not exists app.transactions (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references app.member_cards(id),
  tx_type text not null,
  amount numeric(12,2) not null,
  status text not null default 'processing',
  created_at timestamptz not null default now()
);

-- Audit Log
create table if not exists audit.event_log (
  id bigserial primary key,
  happened_at timestamptz not null default now(),
  actor text,
  action text not null,
  object_type text not null,
  object_id uuid,
  context jsonb not null default '{}'::jsonb
);
