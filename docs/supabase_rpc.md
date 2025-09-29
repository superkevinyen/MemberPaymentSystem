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
    # supabase-py v2 returns an object with .data; v1 returns a Response-like object.
    return getattr(resp, "data", resp)
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
    msg = str(e)
    if "INSUFFICIENT_BALANCE" in msg:
        print("餘額不足，請提醒用戶充值或改用其他方式")
    elif "QR_EXPIRED_OR_INVALID" in msg:
        print("支付碼已失效，請用戶重新出示")
    else:
        raise  # 交由上層處理
```

> Tip: Keep **idempotency keys** stable on retries to avoid double charges.

---

## A. Helpers (internal)

> These are internal helpers; you normally **do not call** them from clients.

### `sec.card_lock_key(card_id uuid) → bigint`
- **Purpose**: Map card UUID → advisory lock key for `pg_advisory_xact_lock()`.
- **Concurrency**: Used inside money-moving RPCs to serialize balance updates.

### `app.compute_level(points int) → int`
- **Purpose**: Points → membership level via `membership_levels` ranges.

### `app.compute_discount(points int) → numeric(4,3)`
- **Purpose**: Points → discount (0..1) via `membership_levels` ranges.

---

## B. Members & Bindings

### 1) `app.create_member_profile(p_name text, p_phone text, p_email text, p_binding_user_org text DEFAULT NULL, p_binding_org_id text DEFAULT NULL, p_default_card_type app.card_type DEFAULT 'standard') → uuid`
- **Returns**: `member_id (uuid)`
- **Purpose**: Create a member + auto‑issue a **standard** card and bind as `owner` (no password). Optionally bind an external identity (e.g., WeChat openid).
- **Side‑effects**: Inserts into `member_profiles`, `member_cards`, `card_bindings`, optional `member_external_identities`, and `audit.event_log`.
- **Permissions**: Recommend service role / platform admin for server‑side; may be exposed to self‑signup if desired.
- **Idempotency**: Not idempotent by itself; callers should guard against duplicate submissions at application layer.
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

**Common errors**
- `EXTERNAL_ID_ALREADY_BOUND` – the (provider, external_id) already linked to another member.

---

### 2) `app.bind_member_to_card(p_card_id uuid, p_member_id uuid, p_role app.bind_role DEFAULT 'member', p_binding_password text DEFAULT NULL) → boolean`
- **Purpose**: Bind a member to a card (`owner` / `admin` / `member` / `viewer`). For shared **prepaid/corporate** cards.
- **Rules**:
  - **standard/voucher**: not shareable; only the owner (created with member) is allowed.
  - **prepaid/corporate**: if `binding_password_hash` is set on the card, you **must** pass correct `p_binding_password`.
  - Card must be `active`.
- **Side‑effects**: Upserts into `card_bindings`, writes `audit.event_log`.
- **Concurrency**: Not balance‑moving; no advisory lock needed.
- **Python**:
```python
ok = rpc("bind_member_to_card", {
    "p_card_id": "<card-uuid>",
    "p_member_id": "<member-uuid>",
    "p_role": "member",
    "p_binding_password": "123456"  # required if card has a password
})
```

**Common errors**
- `CARD_NOT_FOUND_OR_INACTIVE` – card missing or not active.
- `CARD_TYPE_NOT_SHAREABLE` – standard/voucher cannot be shared.
- `CARD_OWNER_NOT_DEFINED` – malformed data; shared card must have at least one owner.
- `INVALID_BINDING_PASSWORD` – wrong password for shared card.

---

### 3) `app.unbind_member_from_card(p_card_id uuid, p_member_id uuid) → boolean`
- **Purpose**: Unbind a member from a card.
- **Safety**: Prevent removing the **last owner** of a card.
- **Side‑effects**: Writes `audit.event_log`.
- **Python**:
```python
ok = rpc("unbind_member_from_card", {
    "p_card_id": "<card-uuid>",
    "p_member_id": "<member-uuid>"
})
```

**Common errors**
- `CANNOT_REMOVE_LAST_OWNER` – unbinding would leave the card without any owner.

---

## C. QR Code

### 4) `app.rotate_card_qr(p_card_id uuid, p_ttl_seconds integer DEFAULT 900) → TABLE(qr_plain text, qr_expires_at timestamptz)`
- **Purpose**: Rotate a card’s QR token; updates `card_qr_state`, appends to `card_qr_history`. Returns **plain** token once.
- **Usage**:
  - **standard**: on‑demand per payment.
  - **prepaid/corporate**: can be periodically rotated by cron (see below).
- **Side‑effects**: `card_qr_state`, `card_qr_history`, `audit.event_log`.
- **Python**:
```python
qr = rpc("rotate_card_qr", {"p_card_id": "<card-uuid>", "p_ttl_seconds": 300})
# -> [{"qr_plain":"...", "qr_expires_at":"..."}]
```

---

### 5) `app.validate_qr_plain(p_qr_plain text) → uuid(card_id)`
- **Purpose**: Verify the plain token against **unexpired** QR entries using bcrypt; returns `card_id`.
- **Errors**: `INVALID_QR`, `QR_EXPIRED_OR_INVALID`.
- **Python**:
```python
card_id = rpc("validate_qr_plain", {"p_qr_plain": "PLAIN_QR_FROM_SCANNER"})
```

---

### 6) `app.revoke_card_qr(p_card_id uuid) → boolean`
- **Purpose**: Immediately expire the current QR code of a card.
- **Python**:
```python
ok = rpc("revoke_card_qr", {"p_card_id": "<card-uuid>"})
```

---

### 7) `app.cron_rotate_qr_tokens(p_ttl_seconds integer DEFAULT 300) → int`
- **Purpose**: Batch‑rotate QR tokens for active `prepaid`/`corporate` cards (server cron job).
- **Returns**: Number of cards rotated.
- **Python**:
```python
affected = rpc("cron_rotate_qr_tokens", {"p_ttl_seconds": 300})
```

---

## D. Payments / Refunds / Recharge

### 8) `app.merchant_charge_by_qr(p_merchant_code text, p_qr_plain text, p_raw_amount numeric, p_idempotency_key text DEFAULT NULL, p_tag jsonb DEFAULT '{}'::jsonb, p_external_order_id text DEFAULT NULL) → TABLE (tx_id uuid, tx_no text, card_id uuid, final_amount numeric, discount numeric)`
- **Purpose**: Merchant scans QR to charge a card.
- **Flow**:
  1. Verify merchant exists & caller is in `merchant_users`.
  2. `validate_qr_plain` ➜ `card_id`; card must be `active` and not expired.
  3. `pg_advisory_xact_lock(card_id)` to serialize balance updates.
  4. Compute discount:  
     - `standard` → `compute_discount(points)`  
     - `prepaid` → `COALESCE(fixed_discount, compute_discount(points))`  
     - `corporate` → `COALESCE(fixed_discount, 1.000)`  
     - `voucher` → not supported (throws)
  5. Idempotency via `idempotency_registry` (and optional `merchant_order_registry`).
  6. Insert `transactions (payment)` → update `member_cards` balance/points/level → write `audit`.
- **Side‑effects**: `transactions`, `member_cards`, `point_ledger` (for standard/prepaid), `audit.event_log`.
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

**Common errors**
- `MERCHANT_NOT_FOUND_OR_INACTIVE`
- `NOT_MERCHANT_USER`
- `INVALID_PRICE`
- `INVALID_QR` / `QR_EXPIRED_OR_INVALID`
- `CARD_NOT_ACTIVE` / `CARD_EXPIRED`
- `INSUFFICIENT_BALANCE`
- `UNSUPPORTED_CARD_TYPE_FOR_PAYMENT`

---

### 9) `app.merchant_refund_tx(p_merchant_code text, p_original_tx_no text, p_refund_amount numeric, p_tag jsonb DEFAULT '{}'::jsonb) → TABLE (refund_tx_id uuid, refund_tx_no text, refunded_amount numeric)`
- **Purpose**: Refund a completed payment (supports partial/multiple refunds).
- **Flow**:
  - Verify merchant & caller.
  - Load original tx; ensure `tx_type='payment'` and status `completed/refunded`.
  - Compute remaining refundable = `final_amount - sum(refunds)`; must be ≥ refund request.
  - Lock by `pg_advisory_xact_lock(card_id)`, insert refund tx, add balance back, update original status if fully refunded.
- **Python**:
```python
refund = rpc("merchant_refund_tx", {
    "p_merchant_code": "SHOP001",
    "p_original_tx_no": "ZF000123",
    "p_refund_amount": 50.00,
    "p_tag": {"reason":"user_request"}
})
```
**Common errors**
- `INVALID_REFUND_AMOUNT`
- `MERCHANT_NOT_FOUND_OR_INACTIVE` / `NOT_MERCHANT_USER`
- `ORIGINAL_TX_NOT_FOUND`
- `ONLY_COMPLETED_PAYMENT_REFUNDABLE`
- `REFUND_EXCEEDS_REMAINING`

---

### 10) `app.user_recharge_card(p_card_id uuid, p_amount numeric, p_payment_method app.pay_method DEFAULT 'wechat', p_tag jsonb DEFAULT '{}'::jsonb, p_idempotency_key text DEFAULT NULL, p_external_order_id text DEFAULT NULL) → TABLE (tx_id uuid, tx_no text, card_id uuid, amount numeric)`
- **Purpose**: Recharge a card (`prepaid` / `corporate` only).
- **Flow**: Idempotency (`idempotency_registry`), optional map to external order, insert recharge tx, update balance, write audit.
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
**Common errors**
- `INVALID_RECHARGE_AMOUNT`
- `CARD_NOT_FOUND_OR_INACTIVE`
- `UNSUPPORTED_CARD_TYPE_FOR_RECHARGE`

---

## E. Points & Levels

### 11) `app.update_points_and_level(p_card_id uuid, p_delta_points int, p_reason text DEFAULT 'manual_adjust') → boolean`
- **Purpose**: Manually adjust points and recompute level/discount (only `standard/prepaid`).
- **Side‑effects**: Updates `member_cards`, appends `point_ledger`, writes `audit`.
- **Python**:
```python
ok = rpc("update_points_and_level", {
    "p_card_id": "<card-uuid>",
    "p_delta_points": 100,
    "p_reason": "promotion_fix"
})
```
**Common errors**
- `CARD_NOT_FOUND_OR_INACTIVE`
- `UNSUPPORTED_CARD_TYPE_FOR_POINTS`

---

## F. Admin & Risk

### 12) `app.freeze_card(p_card_id uuid) → boolean` / `app.unfreeze_card(p_card_id uuid) → boolean`
- **Purpose**: Freeze/unfreeze a card (status toggle). Blocks subsequent charges when inactive.
- **Python**:
```python
rpc("freeze_card", {"p_card_id":"<card-uuid>"})
rpc("unfreeze_card", {"p_card_id":"<card-uuid>"})
```

### 13) `app.admin_suspend_member(p_member_id uuid) → boolean`
- **Purpose**: Suspend a member (blocks card operations).
```python
rpc("admin_suspend_member", {"p_member_id":"<member-uuid>"})
```

### 14) `app.admin_suspend_merchant(p_merchant_id uuid) → boolean`
- **Purpose**: Deactivate a merchant (blocks new charges).
```python
rpc("admin_suspend_merchant", {"p_merchant_id":"<merchant-uuid>"})
```

---

## G. Settlements & Queries

### 15) `app.generate_settlement(p_merchant_id uuid, p_mode app.settlement_mode, p_period_start timestamptz, p_period_end timestamptz) → uuid`
- **Purpose**: Summarize payments − refunds for a merchant and create a settlement row.
- **Modes**: `realtime` | `t_plus_1` | `monthly` (enum in schema).
- **Python**:
```python
sid = rpc("generate_settlement", {
    "p_merchant_id": "<merchant-uuid>",
    "p_mode": "t_plus_1",
    "p_period_start": "2025-09-01T00:00:00Z",
    "p_period_end": "2025-10-01T00:00:00Z"
})
```

### 16) `app.list_settlements(p_merchant_id uuid, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0) → TABLE(...)`
```python
rows = rpc("list_settlements", {"p_merchant_id":"<merchant-uuid>", "p_limit":50, "p_offset":0})
```

### 17) `app.get_member_transactions(p_member_id uuid, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0, p_start_date timestamptz DEFAULT NULL, p_end_date timestamptz DEFAULT NULL) → TABLE(...)`
```python
rows = rpc("get_member_transactions", {
  "p_member_id":"<member-uuid>", "p_limit":20, "p_offset":0,
  "p_start_date":"2025-09-01T00:00:00Z", "p_end_date":"2025-10-01T00:00:00Z"
})
```

### 18) `app.get_merchant_transactions(p_merchant_id uuid, p_limit integer DEFAULT 50, p_offset integer DEFAULT 0, p_start_date timestamptz DEFAULT NULL, p_end_date timestamptz DEFAULT NULL) → TABLE(...)`
```python
rows = rpc("get_merchant_transactions", {
  "p_merchant_id":"<merchant-uuid>", "p_limit":50, "p_offset":0
})
```

### 19) `app.get_transaction_detail(p_tx_no text) → app.transactions`
```python
tx = rpc("get_transaction_detail", {"p_tx_no":"ZF000123"})
```

---

## H. Common error codes (map these in your client)

| Code | Meaning / Action |
|---|---|
| `EXTERNAL_ID_ALREADY_BOUND` | The external identity has been linked to another member. |
| `INVALID_QR` | The QR plain token format is invalid. |
| `QR_EXPIRED_OR_INVALID` | No matching, unexpired QR token; re‑scan or re‑issue. |
| `MERCHANT_NOT_FOUND_OR_INACTIVE` | Merchant code invalid or inactive. |
| `NOT_MERCHANT_USER` | Caller is not a user of the merchant. |
| `CARD_NOT_FOUND_OR_INACTIVE` / `CARD_NOT_ACTIVE` | Card missing or not active. |
| `CARD_EXPIRED` | `expires_at` passed. |
| `CARD_TYPE_NOT_SHAREABLE` | Standard/Voucher cards cannot be shared. |
| `CARD_OWNER_NOT_DEFINED` | No owner binding present for a shared card. |
| `INVALID_BINDING_PASSWORD` | Wrong binding password for shared card. |
| `INSUFFICIENT_BALANCE` | Not enough balance for charge. |
| `INVALID_PRICE` | Raw price must be > 0. |
| `UNSUPPORTED_CARD_TYPE_FOR_PAYMENT` | Voucher or unsupported type for payment. |
| `INVALID_RECHARGE_AMOUNT` | `amount <= 0`. |
| `UNSUPPORTED_CARD_TYPE_FOR_RECHARGE` | Only prepaid/corporate support recharge. |
| `ORIGINAL_TX_NOT_FOUND` | Refund target not found for merchant. |
| `ONLY_COMPLETED_PAYMENT_REFUNDABLE` | Only completed payments are refundable. |
| `REFUND_EXCEEDS_REMAINING` | Refund exceeds remaining refundable amount. |
| `CANNOT_REMOVE_LAST_OWNER` | Prevent removing the last owner. |
| `UNSUPPORTED_CARD_TYPE_FOR_POINTS` | Only standard/prepaid support points ops. |
| `TX_NOT_FOUND` | Transaction not found (detail query). |

**Python mapping helper**

```python
KNOWN = {
    "INVALID_QR": "請重新出示支付碼",
    "QR_EXPIRED_OR_INVALID": "支付碼已失效，請重試",
    "INSUFFICIENT_BALANCE": "餘額不足",
    "UNSUPPORTED_CARD_TYPE_FOR_RECHARGE": "此卡不支援充值",
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
1. `create_member_profile(...)`  → auto standard card + owner binding  
2. *(optional)* include external identity by passing `p_binding_user_org`, `p_binding_org_id`

### Generate payment QR
- **Standard**: app triggers `rotate_card_qr(card_id, 300)` on demand.  
- **Prepaid/Corporate**: schedule `cron_rotate_qr_tokens(300)`; POS consumes fresh token periodically.

### Merchant charge
- Scanner reads QR plain → `merchant_charge_by_qr(...)` with idempotency key (and external order id).

### Refunds
- `merchant_refund_tx(...)` supports partial/multiple refunds until fully refunded.

### Recharge
- `user_recharge_card(...)` with idempotency key and external order id for reconciliation.

### Settlement
- `generate_settlement(...)` then list via `list_settlements(...)`.

---

## J. Permissions & RLS notes

- All writes should go through RPCs; keep base tables locked down by RLS.  
- All RPCs are `SECURITY DEFINER`; grant execution per role group:  
  - **Merchant API**: `merchant_charge_by_qr`, `merchant_refund_tx`, `get_merchant_transactions`, `generate_settlement`, `list_settlements`.  
  - **Member App**: `rotate_card_qr`, `user_recharge_card`, `get_member_transactions`.  
  - **Platform**: `create_member_profile`, `bind_member_to_card`, `unbind_member_from_card`, `freeze_card`, `admin_suspend_*`, `cron_rotate_qr_tokens`.

---

*End of document.*
