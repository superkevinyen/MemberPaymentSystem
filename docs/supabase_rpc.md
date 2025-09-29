
# Supabase RPC Documentation (Commercial Edition, Python Examples)

> **Scope**: This guide documents all RPCs shipped in `mps_rpc.sql` for the Member Payment System (MPS).  
> **Stack**: Supabase (PostgreSQL + RLS), Python client (`supabase-py`).  
> **Style**: Each RPC lists signature, returns, purpose, side‑effects, permissions, idempotency/concurrency notes, common errors, and **Python examples**.

---

## Getting started (Python)

```python
from supabase import create_client, Client

# Use a service role key for server-side jobs, or a user JWT for user/merchant actions.
url = "https://<YOUR-PROJECT-REF>.supabase.co"
key = "<SUPABASE_ANON_OR_SERVICE_ROLE_KEY>"
supabase: Client = create_client(url, key)

def rpc(name: str, params: dict):
    resp = supabase.rpc(name, params).execute()
    if hasattr(resp, "data"):
        return resp.data
    return resp  # supabase-py v2 returns .data; v1 returns response object
```

**Error handling pattern**

```python
try:
    data = rpc("merchant_charge_by_qr", {
        "p_merchant_code": "SHOP001",
        "p_qr_plain": "PLAIN_QR_FROM_SCANNER",
        "p_raw_amount": 299.00,
        "p_idempotency_key": "order-123-abc",
        "p_tag": {"scene": "miniapp"},
        "p_external_order_id": "WX2025..."
    })
except Exception as e:
    # PostgREST returns database errors as messages; map to UX messages:
    msg = str(e)
    if "INSUFFICIENT_BALANCE" in msg:
        # handle gracefully
        pass
    raise
```

> Tip: Keep **idempotency keys** stable on retries to avoid double charges.

---

## A. Helpers (internal)

> These are internal helpers; you normally **do not call** them from clients.

### `app.card_lock_key(card_id uuid) → bigint`
- **Purpose**: Map card UUID → advisory lock key for `pg_advisory_xact_lock()`.
- **Concurrency**: Used inside money-moving RPCs.

### `app.compute_level(points int) → int`
- **Purpose**: Points → membership level via `membership_levels`.

### `app.compute_discount(points int) → numeric(4,3)`
- **Purpose**: Points → discount (0..1).

### `app.generate_qr_token_pair() → TABLE(plain text, hash text)`
- **Purpose**: Generates QR token plain + bcrypt hash (plain is returned only at creation).

---

## B. Members & Bindings

### 1) `app.create_member_profile(name, phone, email, binding_user_org=null, binding_org_id=null, default_card_type='standard') → uuid`
- **Returns**: `member_id (uuid)`
- **Purpose**: Create a member + auto‑issue a default card and bind as `owner`.
- **Side‑effects**: Inserts `member_profiles`, `member_cards`, `card_bindings`, `audit.event_log`.
- **Permissions**: Platform service/admin recommended. You may expose to self‑signup if needed.
- **Python**:
```python
member_id = rpc("create_member_profile", {
    "p_name": "王小明",
    "p_phone": "0988xxxxxx",
    "p_email": "m@test.com",
    "p_binding_user_org": "wechat",
    "p_binding_org_id": "wx_openid_abc",
    "p_default_card_type": "standard"
})
```

### 2) `app.bind_external_identity(member_id, provider, external_id, meta='{}') → boolean`
- **Purpose**: Link a member to an external identity (wechat/alipay/line…). Upsert semantics.
- **Side‑effects**: `member_external_identities`, `audit.event_log`.
- **Uniqueness**: Unique `(provider, external_id)` and `(member_id, provider)`.
- **Python**:
```python
ok = rpc("bind_external_identity", {
    "p_member_id": member_id,
    "p_provider": "wechat",
    "p_external_id": "wx_openid_abc",
    "p_meta": {"nickname": "小明"}
})
```

### 3) `app.bind_member_to_card(card_id, member_id, role='member', binding_password=null) → boolean`
- **Purpose**: Bind a member to a card (owner/admin/member/viewer). For shared prepaid/corporate cards.
- **Rules**:
  - If an owner binding **has a password**, you **must** pass the correct `binding_password`.
  - If no owner password: claiming `owner` requires `member_id == owner_member_id`.
- **Side‑effects**: `card_bindings`, `audit.event_log`.
- **Common errors**: `CARD_NOT_FOUND_OR_INACTIVE`, `INVALID_BINDING_PASSWORD`, `ONLY_OWNER_MEMBER_CAN_CLAIM_OWNER_ROLE`, `CARD_OWNER_NOT_DEFINED`.
- **Python**:
```python
ok = rpc("bind_member_to_card", {
    "p_card_id": "<card-uuid>",
    "p_member_id": member_id,
    "p_role": "member",
    "p_binding_password": "123456"
})
```

### 4) `app.unbind_member_from_card(card_id, member_id) → boolean`
- **Purpose**: Unbind a member from a card. Protects against removing the **last owner**.
- **Side‑effects**: `audit.event_log`.
- **Errors**: `CANNOT_REMOVE_LAST_OWNER`.
- **Python**:
```python
ok = rpc("unbind_member_from_card", {
    "p_card_id": "<card-uuid>",
    "p_member_id": member_id
})
```

---

## C. QR Code

### 5) `app.rotate_card_qr(card_id, ttl_seconds=900) → TABLE(qr_plain text, qr_expires_at timestamptz)`
- **Purpose**: Rotate QR for a card; updates `card_qr_state`, appends `card_qr_history`. Returns **plain** once.
- **Side‑effects**: `card_qr_state`, `card_qr_history`, `audit.event_log`.
- **Python**:
```python
qr = rpc("rotate_card_qr", {"p_card_id": "<card-uuid>", "p_ttl_seconds": 300})
# qr = [{"qr_plain":"...", "qr_expires_at":"..."}]
```

### 6) `app.validate_qr_plain(qr_plain) → uuid(card_id)`
- **Purpose**: Verify a plain token against **unexpired** QR state (bcrypt). Returns `card_id` or raises.
- **Errors**: `INVALID_QR`, `QR_EXPIRED_OR_INVALID`.
- **Python**:
```python
card_id = rpc("validate_qr_plain", {"p_qr_plain": "PLAIN_QR_FROM_SCANNER"})
```

### 7) `app.revoke_card_qr(card_id) → boolean`
- **Purpose**: Immediately expire the current QR for a card.
- **Python**:
```python
ok = rpc("revoke_card_qr", {"p_card_id": "<card-uuid>"})
```

### 8) `app.cron_rotate_qr_tokens(ttl_seconds=300) → int`
- **Purpose**: Batch rotate QR for `prepaid/corporate` cards (server cron job).
- **Returns**: Number of cards affected.
- **Python**:
```python
affected = rpc("cron_rotate_qr_tokens", {"p_ttl_seconds": 300})
```

---

## D. Payments / Refunds / Recharge

### 9) `app.merchant_charge_by_qr(merchant_code, qr_plain, raw_amount, idempotency_key=null, tag='{}', external_order_id=null)`  
**→ TABLE(tx_id uuid, tx_no text, card_id uuid, final_amount numeric, discount numeric)**

- **Purpose**: Merchant scans QR to charge.
- **Flow**:
  1. Verify merchant exists & caller is in `merchant_users`.
  2. `validate_qr_plain` → `card_id`.
  3. `pg_advisory_xact_lock(card_id)` for concurrency.
  4. Discount rules:  
     - `standard` → `compute_discount(points)`  
     - `prepaid` → prefer `fixed_discount` else `compute_discount(points)`  
     - `corporate` → `coalesce(fixed_discount, 1.000)`  
     - `voucher` → not supported (throws)  
  5. Idempotency via `idempotency_registry` (+ optional `merchant_order_registry`).
  6. Deduct balance; add points for `standard/prepaid`.
  7. Mark transaction as `completed`; write `audit`.
- **Errors**: `MERCHANT_NOT_FOUND_OR_INACTIVE`, `NOT_MERCHANT_USER`, `INVALID_QR`, `CARD_NOT_ACTIVE`, `CARD_EXPIRED`, `INSUFFICIENT_BALANCE`, `UNSUPPORTED_CARD_TYPE_FOR_PAYMENT`.
- **Python**:
```python
charge = rpc("merchant_charge_by_qr", {
    "p_merchant_code": "SHOP001",
    "p_qr_plain": "PLAIN_QR_FROM_SCANNER",
    "p_raw_amount": 299.00,
    "p_idempotency_key": "order-123-abc",
    "p_tag": {"scene":"miniapp","campaign":"october"},
    "p_external_order_id": "WX2025..."
})
# -> [{"tx_id":"...", "tx_no":"...", "card_id":"...", "final_amount": 284.05, "discount": 0.95}]
```

### 10) `app.merchant_refund_tx(merchant_code, original_tx_no, refund_amount, tag='{}')`  
**→ TABLE(refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)**

- **Purpose**: Refund a completed payment (supports partial/multiple refunds).
- **Flow**: Lock same card; compute remaining refundable; create refund tx; add balance back.
- **Errors**: `ORIGINAL_TX_NOT_FOUND`, `ONLY_COMPLETED_PAYMENT_REFUNDABLE`, `REFUND_EXCEEDS_REMAINING`, `NOT_MERCHANT_USER`.
- **Python**:
```python
refund = rpc("merchant_refund_tx", {
    "p_merchant_code": "SHOP001",
    "p_original_tx_no": "PAY0000000123",
    "p_refund_amount": 50.00,
    "p_tag": {"reason":"user_request"}
})
```

### 11) `app.user_recharge_card(card_id, amount, payment_method='wechat', tag='{}', idempotency_key=null, external_order_id=null)`  
**→ TABLE(tx_id uuid, tx_no text, card_id uuid, amount numeric)**

- **Purpose**: Recharge a card (user/self or 3rd‑party payment callback).
- **Errors**: `INVALID_RECHARGE_AMOUNT`, `CARD_NOT_FOUND_OR_INACTIVE`.
- **Python**:
```python
recharge = rpc("user_recharge_card", {
    "p_card_id": "<card-uuid>",
    "p_amount": 100.0,
    "p_payment_method": "wechat",
    "p_tag": {"channel":"miniapp"},
    "p_idempotency_key": "topup-abc-001",
    "p_external_order_id": "WXTOPUP2025..."
})
```

---

## E. Points & Levels / 積分等級

### 12) `app.update_points_and_level(card_id, delta_points, reason='manual_adjust') → boolean`
- **Purpose**: Manually adjust points and sync level/discount (`standard/prepaid`).
- **Side‑effects**: Writes `point_ledger`, `audit.event_log`.
- **Python**:
```python
ok = rpc("update_points_and_level", {
    "p_card_id": "<card-uuid>",
    "p_delta_points": 100,
    "p_reason": "promotion_fix"
})
```

---

## F. Settlements & Reports

### 13) `app.generate_settlement(merchant_id, mode, period_start, period_end) → uuid`
- **Purpose**: Summarize net amount (payments − refunds) & count for a period; create a settlement row.
- **Permissions**: Caller must be in merchant's `merchant_users`.
- **Python**:
```python
sid = rpc("generate_settlement", {
    "p_merchant_id": "<merchant-uuid>",
    "p_mode": "t_plus_1",  # or "realtime", "monthly"
    "p_period_start": "2025-09-01T00:00:00Z",
    "p_period_end": "2025-10-01T00:00:00Z"
})
```

### 14) `app.list_settlements(merchant_id, limit=50, offset=0)`  
**→ TABLE(id, period_start, period_end, total_amount, total_tx_count, status, created_at)**
```python
rows = rpc("list_settlements", {"p_merchant_id":"<merchant-uuid>", "p_limit":50, "p_offset":0})
```

### 15) `app.get_member_transactions(member_id, limit=50, offset=0, start_date=null, end_date=null)`  
**→ TABLE(id, tx_no, tx_type, card_id, merchant_id, final_amount, status, created_at, total_count)**
```python
rows = rpc("get_member_transactions", {
  "p_member_id":"<member-uuid>", "p_limit":20, "p_offset":0,
  "p_start_date":"2025-09-01T00:00:00Z", "p_end_date":"2025-10-01T00:00:00Z"
})
```

### 16) `app.get_merchant_transactions(merchant_id, limit=50, offset=0, start_date=null, end_date=null)`  
**→ TABLE(id, tx_no, tx_type, card_id, final_amount, status, created_at, total_count)**
```python
rows = rpc("get_merchant_transactions", {
  "p_merchant_id":"<merchant-uuid>", "p_limit":50, "p_offset":0
})
```

### 17) `app.get_transaction_detail(tx_no) → app.transactions`
```python
tx = rpc("get_transaction_detail", {"p_tx_no":"PAY0000000123"})
```

---

## G. Admin Helpers

### 18) `app.freeze_card(card_id) → boolean` / `app.unfreeze_card(card_id) → boolean`
```python
rpc("freeze_card", {"p_card_id":"<card-uuid>"})
rpc("unfreeze_card", {"p_card_id":"<card-uuid>"})
```

### 19) `app.admin_suspend_member(member_id) → boolean` / `app.admin_suspend_merchant(merchant_id) → boolean`
```python
rpc("admin_suspend_member", {"p_member_id":"<member-uuid>"})
rpc("admin_suspend_merchant", {"p_merchant_id":"<merchant-uuid>"})
```

---

## H. Common error codes (map these in your client)

| Code | Meaning / Action |
|---|---|
| `INVALID_QR` | The QR plain token format is invalid. |
| `QR_EXPIRED_OR_INVALID` | No matching, unexpired QR token; re‑scan or re‑issue. |
| `MERCHANT_NOT_FOUND_OR_INACTIVE` | Merchant code invalid or inactive. |
| `NOT_MERCHANT_USER` | Caller is not a user of the merchant. |
| `CARD_NOT_FOUND_OR_INACTIVE` / `CARD_NOT_ACTIVE` | Card missing or not active. |
| `CARD_EXPIRED` | `expires_at` passed. |
| `INSUFFICIENT_BALANCE` | Not enough balance for charge. |
| `UNSUPPORTED_CARD_TYPE_FOR_PAYMENT` | Voucher flow not supported in this RPC. |
| `INVALID_RECHARGE_AMOUNT` | `amount <= 0`. |
| `ORIGINAL_TX_NOT_FOUND` | Refund target not found for merchant. |
| `ONLY_COMPLETED_PAYMENT_REFUNDABLE` | Only completed payments are refundable. |
| `REFUND_EXCEEDS_REMAINING` | Refund exceeds remaining refundable amount. |
| `INVALID_BINDING_PASSWORD` | Wrong binding password for shared card. |
| `ONLY_OWNER_MEMBER_CAN_CLAIM_OWNER_ROLE` | Non-owner member tried to claim owner role. |
| `CANNOT_REMOVE_LAST_OWNER` | Prevent removing the last owner. |
| `CARD_OWNER_NOT_DEFINED` | Data inconsistency; card has no owner binding defined. |

**Python mapping helper**

```python
KNOWN = {
    "INVALID_QR": "請重新出示支付碼",
    "QR_EXPIRED_OR_INVALID": "支付碼已失效，請重試",
    "INSUFFICIENT_BALANCE": "餘額不足",
    # ... extend as needed
}
def humanize_error(exc: Exception) -> str:
    msg = str(exc)
    for k, v in KNOWN.items():
        if k in msg:
            return v
    return "操作失敗，請稍後再試"
```

---

## I. Typical flows

### Member signup
1. `create_member_profile(...)`
2. `bind_external_identity(...)` (wechat, etc.)

### Generate payment QR
- Standard card: app triggers `rotate_card_qr(card_id, 300)` on demand.
- Prepaid/corporate: schedule `cron_rotate_qr_tokens(300)`; clients read the current QR plain from rotation call.

### Merchant charge
- Scanner reads QR plain → `merchant_charge_by_qr(...)` with idempotency key.

### Refunds
- `merchant_refund_tx(...)` supports partial/multiple refunds.

### Recharge
- `user_recharge_card(...)` with idempotency key and external order id for reconciliation.

### Settlement
- `generate_settlement(...)` then list via `list_settlements(...)`.

---

## J. Permissions & RLS notes

- Prefer routing **all writes through RPC**; keep table writes locked down by RLS.  
- Grant execution per role group (examples):  
  - **Merchant API**: `merchant_charge_by_qr`, `merchant_refund_tx`, `get_merchant_transactions`, `generate_settlement`, `list_settlements`.  
  - **Member App**: `rotate_card_qr`, `user_recharge_card`, `get_member_transactions`.  
  - **Platform**: `create_member_profile`, `bind_external_identity`, `bind_member_to_card`, `unbind_member_from_card`, `freeze_card`, `admin_suspend_*`, `cron_rotate_qr_tokens`.

---

*End of document.*
