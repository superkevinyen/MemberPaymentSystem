# MPS API 端點規格書

## 📋 API 概述

MPS API 提供完整的 HTTP REST 接口，包裝現有的 Supabase RPC 函數，支持會員、商戶、管理員三種角色的業務操作。

## 🔐 認證機制

### 認證流程

所有 API 調用（除登入外）都需要在請求頭中包含 JWT Token：

```http
Authorization: Bearer {jwt_token}
```

### JWT Token 結構

```json
{
  "sub": "user_id",
  "role": "member|merchant|admin", 
  "name": "用戶名稱",
  "permissions": ["permission1", "permission2"],
  "iat": 1640995200,
  "exp": 1641081600,
  "session_id": "uuid"
}
```

---

## 🛣️ API 端點詳細規格

### 🔑 認證相關 API

#### POST /auth/login
**功能**：用戶登入認證

**請求體**：
```json
{
  "role": "member|merchant|admin",
  "identifier": "user_identifier",
  "password": "optional_password",
  "operator": "optional_operator_name",
  "admin_code": "optional_admin_code"
}
```

**響應**：
```json
{
  "success": true,
  "token": "jwt_token_string",
  "user_info": {
    "id": "user_id",
    "name": "用戶名稱", 
    "role": "member",
    "permissions": ["member:read_cards", "member:generate_qr"]
  },
  "expires_at": "2024-01-01T12:00:00Z"
}
```

**錯誤響應**：
```json
{
  "success": false,
  "error": "認證失敗：會員不存在或狀態異常"
}
```

#### POST /auth/logout
**功能**：用戶登出

**請求頭**：`Authorization: Bearer {token}`

**響應**：
```json
{
  "success": true,
  "message": "登出成功"
}
```

#### GET /auth/me
**功能**：獲取當前用戶信息

**請求頭**：`Authorization: Bearer {token}`

**響應**：
```json
{
  "user_info": {
    "id": "user_id",
    "name": "用戶名稱",
    "role": "member",
    "permissions": ["member:read_cards"]
  },
  "session_info": {
    "expires_at": "2024-01-01T12:00:00Z",
    "issued_at": "2024-01-01T00:00:00Z"
  }
}
```

---

### 👤 會員相關 API

#### GET /member/cards
**功能**：獲取會員卡片列表  
**權限**：`member:read_cards`  
**對應 RPC**：查詢 `member_cards` 和 `card_bindings` 表

**響應**：
```json
{
  "cards": [
    {
      "id": "card_uuid",
      "card_no": "STD00000001",
      "card_type": "standard",
      "balance": 1000.50,
      "points": 1000,
      "level": 1,
      "discount_rate": 0.95,
      "status": "active",
      "expires_at": null,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "summary": {
    "total_cards": 3,
    "active_cards": 2,
    "total_balance": 2500.75,
    "total_points": 2500
  }
}
```

#### POST /member/qr/generate
**功能**：生成付款 QR 碼  
**權限**：`member:generate_qr`  
**對應 RPC**：[`rotate_card_qr`](../../rpc/mps_rpc.sql:158)

**請求體**：
```json
{
  "card_id": "card_uuid",
  "ttl_seconds": 900
}
```

**響應**：
```json
{
  "qr_plain": "base64_encoded_qr_string",
  "expires_at": "2024-01-01T12:15:00Z",
  "card_info": {
    "card_no": "STD00000001",
    "card_type": "standard",
    "balance": 1000.50
  },
  "ttl_seconds": 900
}
```

#### POST /member/recharge
**功能**：充值卡片  
**權限**：`member:recharge`  
**對應 RPC**：[`user_recharge_card`](../../rpc/mps_rpc.sql:467)

**請求體**：
```json
{
  "card_id": "card_uuid",
  "amount": 500.00,
  "payment_method": "wechat|alipay|bank",
  "external_order_id": "optional_external_id"
}
```

**響應**：
```json
{
  "success": true,
  "transaction": {
    "tx_id": "tx_uuid",
    "tx_no": "RCG0000000123",
    "card_id": "card_uuid",
    "amount": 500.00,
    "payment_method": "wechat",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### GET /member/transactions
**功能**：獲取會員交易記錄  
**權限**：`member:read_transactions`  
**對應 RPC**：[`get_member_transactions`](../../rpc/mps_rpc.sql:710)

**查詢參數**：
- `limit`: 每頁數量 (默認 20)
- `offset`: 偏移量 (默認 0)
- `start_date`: 開始日期 (可選)
- `end_date`: 結束日期 (可選)

**響應**：
```json
{
  "transactions": [
    {
      "id": "tx_uuid",
      "tx_no": "PAY0000000123",
      "tx_type": "payment",
      "card_id": "card_uuid",
      "merchant_id": "merchant_uuid",
      "raw_amount": 299.00,
      "final_amount": 284.05,
      "discount_applied": 0.95,
      "points_earned": 299,
      "status": "completed",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 0,
    "page_size": 20,
    "total_count": 156,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

#### POST /member/bind-card
**功能**：綁定卡片到會員  
**權限**：`member:bind_card`  
**對應 RPC**：[`bind_member_to_card`](../../rpc/mps_rpc.sql:74)

**請求體**：
```json
{
  "card_id": "card_uuid",
  "role": "member|viewer",
  "binding_password": "optional_password"
}
```

**響應**：
```json
{
  "success": true,
  "binding": {
    "card_id": "card_uuid",
    "member_id": "member_uuid",
    "role": "member",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

---

### 🏪 商戶相關 API

#### POST /merchant/charge
**功能**：掃碼收款  
**權限**：`merchant:charge`  
**對應 RPC**：[`merchant_charge_by_qr`](../../rpc/mps_rpc.sql:274)

**請求體**：
```json
{
  "qr_plain": "customer_qr_code_string",
  "amount": 299.00,
  "external_order_id": "optional_order_id",
  "tag": {
    "source": "pos_cli",
    "operator": "李小華"
  }
}
```

**響應**：
```json
{
  "success": true,
  "transaction": {
    "tx_id": "tx_uuid",
    "tx_no": "PAY0000000123",
    "card_id": "card_uuid",
    "raw_amount": 299.00,
    "final_amount": 284.05,
    "discount": 0.95,
    "points_earned": 299,
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "customer_info": {
    "card_no": "STD00000001",
    "card_type": "standard",
    "member_level": 1
  }
}
```

#### POST /merchant/refund
**功能**：退款處理  
**權限**：`merchant:refund`  
**對應 RPC**：[`merchant_refund_tx`](../../rpc/mps_rpc.sql:401)

**請求體**：
```json
{
  "original_tx_no": "PAY0000000123",
  "refund_amount": 100.00,
  "reason": "客戶要求退款",
  "tag": {
    "source": "pos_cli",
    "operator": "李小華"
  }
}
```

**響應**：
```json
{
  "success": true,
  "refund": {
    "refund_tx_id": "refund_uuid",
    "refund_tx_no": "REF0000000456",
    "refunded_amount": 100.00,
    "original_tx_no": "PAY0000000123",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "remaining_refundable": 184.05
}
```

#### GET /merchant/transactions
**功能**：獲取商戶交易記錄  
**權限**：`merchant:read_transactions`  
**對應 RPC**：[`get_merchant_transactions`](../../rpc/mps_rpc.sql:741)

**查詢參數**：
- `limit`: 每頁數量 (默認 20)
- `offset`: 偏移量 (默認 0)
- `start_date`: 開始日期 (可選)
- `end_date`: 結束日期 (可選)

**響應**：
```json
{
  "transactions": [
    {
      "id": "tx_uuid",
      "tx_no": "PAY0000000123",
      "tx_type": "payment",
      "card_id": "card_uuid",
      "final_amount": 284.05,
      "status": "completed",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 0,
    "page_size": 20,
    "total_count": 89,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

#### GET /merchant/daily-summary
**功能**：獲取商戶日交易摘要  
**權限**：`merchant:read_summary`  
**對應 RPC**：基於 [`get_merchant_transactions`](../../rpc/mps_rpc.sql:741) 的統計

**查詢參數**：
- `date`: 查詢日期 (YYYY-MM-DD，默認今日)

**響應**：
```json
{
  "date": "2024-01-01",
  "summary": {
    "total_count": 45,
    "payment_count": 42,
    "refund_count": 3,
    "payment_amount": 12580.50,
    "refund_amount": 350.00,
    "net_amount": 12230.50
  },
  "hourly_stats": [
    {"hour": 9, "count": 5, "amount": 1250.00},
    {"hour": 10, "count": 8, "amount": 2100.00}
  ]
}
```

#### POST /merchant/settlements
**功能**：生成結算報表  
**權限**：`merchant:generate_settlement`  
**對應 RPC**：[`generate_settlement`](../../rpc/mps_rpc.sql:655)

**請求體**：
```json
{
  "mode": "realtime|t_plus_1|monthly",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-31T23:59:59Z"
}
```

**響應**：
```json
{
  "success": true,
  "settlement": {
    "id": "settlement_uuid",
    "period_start": "2024-01-01T00:00:00Z",
    "period_end": "2024-01-31T23:59:59Z",
    "mode": "monthly",
    "total_amount": 125800.50,
    "total_tx_count": 1250,
    "status": "pending",
    "created_at": "2024-02-01T00:00:00Z"
  }
}
```

#### GET /merchant/settlements
**功能**：獲取結算記錄列表  
**權限**：`merchant:read_settlements`  
**對應 RPC**：[`list_settlements`](../../rpc/mps_rpc.sql:690)

**查詢參數**：
- `limit`: 每頁數量 (默認 50)
- `offset`: 偏移量 (默認 0)

**響應**：
```json
{
  "settlements": [
    {
      "id": "settlement_uuid",
      "period_start": "2024-01-01T00:00:00Z",
      "period_end": "2024-01-31T23:59:59Z",
      "mode": "monthly",
      "total_amount": 125800.50,
      "total_tx_count": 1250,
      "status": "settled",
      "created_at": "2024-02-01T00:00:00Z"
    }
  ],
  "pagination": {
    "current_page": 0,
    "page_size": 50,
    "total_count": 12,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### 👨‍💼 管理員相關 API

#### POST /admin/members
**功能**：創建新會員  
**權限**：`admin:create_member`  
**對應 RPC**：[`create_member_profile`](../../rpc/mps_rpc.sql:15)

**請求體**：
```json
{
  "name": "張小明",
  "phone": "13800138000",
  "email": "zhang@example.com",
  "binding_user_org": "wechat",
  "binding_org_id": "wx_openid_123",
  "default_card_type": "standard"
}
```

**響應**：
```json
{
  "success": true,
  "member": {
    "member_id": "member_uuid",
    "name": "張小明",
    "phone": "13800138000",
    "email": "zhang@example.com",
    "status": "active",
    "created_at": "2024-01-01T12:00:00Z"
  },
  "default_card": {
    "card_id": "card_uuid",
    "card_no": "STD00000001",
    "card_type": "standard",
    "status": "active"
  }
}
```

#### POST /admin/cards/freeze
**功能**：凍結卡片  
**權限**：`admin:manage_cards`  
**對應 RPC**：[`freeze_card`](../../rpc/mps_rpc.sql:591)

**請求體**：
```json
{
  "card_id": "card_uuid",
  "reason": "風險控制"
}
```

**響應**：
```json
{
  "success": true,
  "card": {
    "card_id": "card_uuid",
    "card_no": "STD00000001",
    "status": "inactive",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "卡片凍結成功"
}
```

#### POST /admin/cards/unfreeze
**功能**：解凍卡片  
**權限**：`admin:manage_cards`  
**對應 RPC**：[`unfreeze_card`](../../rpc/mps_rpc.sql:606)

**請求體**：
```json
{
  "card_id": "card_uuid",
  "reason": "風險解除"
}
```

**響應**：
```json
{
  "success": true,
  "card": {
    "card_id": "card_uuid",
    "card_no": "STD00000001", 
    "status": "active",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "卡片解凍成功"
}
```

#### POST /admin/points/adjust
**功能**：調整積分和等級  
**權限**：`admin:adjust_points`  
**對應 RPC**：[`update_points_and_level`](../../rpc/mps_rpc.sql:546)

**請求體**：
```json
{
  "card_id": "card_uuid",
  "delta_points": 1000,
  "reason": "活動獎勵"
}
```

**響應**：
```json
{
  "success": true,
  "adjustment": {
    "card_id": "card_uuid",
    "points_before": 2000,
    "points_after": 3000,
    "delta_points": 1000,
    "level_before": 1,
    "level_after": 2,
    "reason": "活動獎勵",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

#### POST /admin/members/suspend
**功能**：暫停會員  
**權限**：`admin:suspend_member`  
**對應 RPC**：[`admin_suspend_member`](../../rpc/mps_rpc.sql:621)

**請求體**：
```json
{
  "member_id": "member_uuid",
  "reason": "違規行為"
}
```

**響應**：
```json
{
  "success": true,
  "member": {
    "member_id": "member_uuid",
    "name": "張小明",
    "status": "suspended",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "會員暫停成功"
}
```

#### POST /admin/qr/batch-rotate
**功能**：批量輪換 QR 碼  
**權限**：`admin:batch_operations`  
**對應 RPC**：[`cron_rotate_qr_tokens`](../../rpc/mps_rpc.sql:235)

**請求體**：
```json
{
  "ttl_seconds": 300
}
```

**響應**：
```json
{
  "success": true,
  "result": {
    "affected_cards": 1250,
    "ttl_seconds": 300,
    "executed_at": "2024-01-01T12:00:00Z"
  },
  "message": "批量 QR 碼輪換完成"
}
```

#### GET /admin/statistics
**功能**：獲取系統統計信息  
**權限**：`admin:read_statistics`  
**對應 RPC**：多個表的統計查詢

**響應**：
```json
{
  "system_stats": {
    "members": {
      "total": 8567,
      "active": 8234,
      "suspended": 333
    },
    "cards": {
      "total": 12345,
      "active": 11890,
      "inactive": 455
    },
    "merchants": {
      "total": 234,
      "active": 228,
      "inactive": 6
    }
  },
  "today_stats": {
    "date": "2024-01-01",
    "transactions": {
      "total_count": 1234,
      "payment_count": 1198,
      "refund_count": 36,
      "payment_amount": 125800.50,
      "refund_amount": 1250.00
    },
    "qr_generated": 2456,
    "new_members": 15
  },
  "generated_at": "2024-01-01T12:00:00Z"
}
```

---

### 🔧 通用 API

#### POST /common/qr/validate
**功能**：驗證 QR 碼  
**權限**：`merchant:charge`  
**對應 RPC**：[`validate_qr_plain`](../../rpc/mps_rpc.sql:206)

**請求體**：
```json
{
  "qr_plain": "qr_code_string"
}
```

**響應**：
```json
{
  "valid": true,
  "card_id": "card_uuid",
  "card_info": {
    "card_no": "STD00000001",
    "card_type": "standard",
    "balance": 1000.50,
    "status": "active"
  }
}
```

#### GET /common/transactions/{tx_no}
**功能**：獲取交易詳情  
**權限**：任意已登入用戶  
**對應 RPC**：[`get_transaction_detail`](../../rpc/mps_rpc.sql:769)

**路徑參數**：
- `tx_no`: 交易號

**響應**：
```json
{
  "transaction": {
    "id": "tx_uuid",
    "tx_no": "PAY0000000123",
    "tx_type": "payment",
    "card_id": "card_uuid",
    "merchant_id": "merchant_uuid",
    "raw_amount": 299.00,
    "discount_applied": 0.95,
    "final_amount": 284.05,
    "points_earned": 299,
    "status": "completed",
    "reason": null,
    "payment_method": "balance",
    "tag": {
      "source": "pos_cli",
      "operator": "李小華"
    },
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

---

## 🚨 錯誤處理規格

### 標準錯誤響應格式

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "用戶友好的錯誤信息",
    "details": {
      "field": "具體錯誤字段",
      "value": "錯誤值",
      "suggestion": "解決建議"
    },
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### 錯誤碼映射

| RPC 錯誤碼 | HTTP 狀態碼 | API 錯誤碼 | 中文信息 |
|------------|-------------|------------|----------|
| `INSUFFICIENT_BALANCE` | 400 | `INSUFFICIENT_BALANCE` | 餘額不足，請充值後再試 |
| `QR_EXPIRED_OR_INVALID` | 400 | `QR_EXPIRED_OR_INVALID` | QR 碼已過期或無效，請重新生成 |
| `NOT_MERCHANT_USER` | 403 | `NOT_MERCHANT_USER` | 您沒有此商戶的操作權限 |
| `CARD_NOT_FOUND_OR_INACTIVE` | 404 | `CARD_NOT_FOUND_OR_INACTIVE` | 卡片不存在或未