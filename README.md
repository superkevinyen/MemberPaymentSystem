
# Member Payment System (MPS)

A **commercial‑grade** membership & payment backend built on **Supabase (PostgreSQL + RLS)**.  
It supports **member profiles, multi‑type cards, QR‑based charging, refunds, recharges, settlements, audit logging, and external identity binding (e.g., WeChat)**.

This repo ships:
- `mps_schema.sql` — all tables, types, indexes, RLS, helpers (idempotency registries, QR state, etc.).
- `mps_rpc.sql` — **SECURITY DEFINER** RPCs with advisory locks and idempotency.
- `supabase_rpc.md` — full RPC handbook (this project’s API), with **Python** examples.
- `README.md` — this file.
- `Architecture.md` — deep dive design notes and diagrams.

> The system separates **platform/Admin auth** (Supabase `auth.users`) from **business members** (`member_profiles`). Real members live in your app DB, not in Supabase auth, but you can map admin/merchant operators via `auth.users` as needed.

---

## ✨ Features

- **Members & external identities**
  - `member_profiles` minimal core fields
  - `member_external_identities` for WeChat/Alipay/Line… (unique per provider)
- **Cards**
  - Card types: `standard`, `prepaid`, `corporate`, `voucher`
  - Shared cards via `card_bindings` with roles `owner/admin/member/viewer`
  - Owner binding can be protected by **binding password hash**
- **QR payments**
  - Rotating QR tokens per card (`card_qr_state` + `card_qr_history`)
  - **Never store QR plain**, only bcrypt hashes
- **Transactions**
  - `payment`, `refund`, `recharge` with **idempotency** and **advisory locks**
  - `tag jsonb` for 3rd‑party metadata
  - `point_ledger` + `membership_levels` for points/level/discount model
- **Merchants & settlements**
  - Merchant users (`merchant_users`) operate RPCs
  - `settlements` supports modes `realtime | t_plus_1 | monthly`
- **Audit & security**
  - Every sensitive action logged to `audit.event_log`
  - RLS defaults to **deny direct writes**; mutate only via RPC

---

## 🚀 Quick start

### 1) Create a Supabase project
- Ensure extension **`pgcrypto`** is enabled.

### 2) Apply SQL
Open **SQL Editor** and run, in order:

1. `mps_schema.sql` (creates all types/tables/indexes/RLS).
2. `mps_rpc.sql` (drops & recreates all RPCs).

> Safe to re‑run: both scripts drop or upsert objects where sensible.

### 3) Python client setup

```bash
pip install supabase
```

```python
from supabase import create_client, Client

SUPABASE_URL = "https://<PROJECT-REF>.supabase.co"
SUPABASE_KEY = "<ANON_OR_SERVICE_ROLE_KEY>"  # service role for server jobs

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def rpc(fname: str, params: dict):
    # Works with supabase-py v2
    res = supabase.rpc(fname, params).execute()
    return getattr(res, "data", res)
```

### 4) Sanity test

```python
# 1) Create a member (auto issues a default standard card)
member_id = rpc("create_member_profile", {
    "p_name": "Alice",
    "p_phone": "13800000000",
    "p_email": "alice@example.com",
    "p_binding_user_org": "wechat",
    "p_binding_org_id": "wx_openid_xxx",
    "p_default_card_type": "standard"
})

# 2) Rotate the card’s QR (get a one-time plain token for the app)
qr = rpc("rotate_card_qr", {"p_card_id": "<card-uuid>", "p_ttl_seconds": 300})

# 3) Simulate a merchant charge
charge = rpc("merchant_charge_by_qr", {
    "p_merchant_code": "SHOP001",
    "p_qr_plain": qr[0]["qr_plain"],
    "p_raw_amount": 199.00,
    "p_idempotency_key": "order-xyz-1",
    "p_tag": {"scene": "miniapp"}
})
```

---

## 🔐 Security model (high level)

- **Auth separation**
  - **Platform/Admin users**: Supabase `auth.users` (create merchants, operate POS, run settlement).
  - **Members**: `member_profiles` (real customers). No tight coupling to `auth.users`.
- **RLS**
  - Tables are RLS‑enabled and default‑deny. Reads are whitelisted where safe.
  - **All writes** happen through RPCs (SECURITY DEFINER), so you can keep tables locked down.
- **Secrets & hashes**
  - Fields ending with `_password_hash` store **bcrypt** hashes only.
  - **QR tokens** are **never stored** as plain text; only hashed.
- **Concurrency**
  - Money‑moving RPCs use `pg_advisory_xact_lock` keyed by card id.
- **Idempotency**
  - `idempotency_registry` / `merchant_order_registry` / `tx_registry` guarantee safe retries.

---

## 🧩 Roles (suggested)

- **platform_admin / service**: run provisioning & admin helpers, settlements, batch jobs.
- **merchant_api**: can call merchant RPCs (`merchant_charge_by_qr`, `merchant_refund_tx`, etc.).
- **member_app**: can rotate own QR, recharge own card, read own transactions.

Use `GRANT EXECUTE ON FUNCTION ... TO <role>` to whitelist per group. Keep direct table writes closed via RLS.

---

## 🧪 Testing checklist (minimum)

- Charge: success, idempotent retry, insufficient balance, QR expired
- Refund: partial then full, multiple partials, not refundable states
- Recharge: idempotent retry, invalid amount
- Points/Level: upgrade boundaries (min/max), discount correctness
- QR: rotation TTL, revoke, cron rotation for shared cards
- Settlement: period edges, empty periods, refunds netting
- RLS: ensure no direct writes from `anon`/`authenticated`

---

## 🛠 Operations

- **QR Rotation cron**: call `cron_rotate_qr_tokens(300)` for `prepaid/corporate` pools.
- **Settlement scheduler**: call `generate_settlement(...)` per merchant & SLA.
- **Backups**: use Supabase PITR / backups for `app` + `audit` schemas.
- **Monitoring**: track `audit.event_log` and DB errors emitted via PostgREST.

---

## 📚 Documentation

See **`supabase_rpc.md`** for detailed RPC usage with Python examples.  
See **`Architecture.md`** for design, diagrams, and scalability guidance.
