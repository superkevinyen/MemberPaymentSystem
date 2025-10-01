# MPS Python 文字 UI 規格書

## 📋 基於現有 RPC 的功能分析

### 🔍 現有 RPC 功能清單

基於 [`rpc/mps_rpc.sql`](../rpc/mps_rpc.sql) 分析，我們有以下可用的 RPC 函數：

#### A. 認證與會員管理
- `member_login()` - 會員登入（手機/會員號 + 密碼）
- `merchant_login()` - 商戶登入（商戶代碼 + 密碼）
- `logout_session()` - 登出（刪除 session）
- `load_session()` - 加載 session（驗證有效性）
- `create_member_profile()` - 創建會員（自動生成標準卡）
- `set_member_password()` - 設置會員密碼
- `set_merchant_password()` - 設置商戶密碼
- `bind_member_to_card()` - 綁定會員到卡片
- `unbind_member_from_card()` - 解綁會員卡片

#### B. QR 碼管理
- `rotate_card_qr()` - 生成/刷新 QR 碼（只有 Member/Admin 可用，Merchant 不可）
- `validate_qr_plain()` - 驗證 QR 碼
- `revoke_card_qr()` - 撤銷 QR 碼
- `cron_rotate_qr_tokens()` - 批量輪換 QR 碼（只適用於 Corporate Card）

#### C. 交易處理
- `merchant_charge_by_qr()` - 商戶掃碼收款（支持 session）
- `merchant_refund_tx()` - 商戶退款（支持多次部分退款）
- `user_recharge_card()` - 用戶充值（只支持 Standard Card）

#### D. 積分等級
- `update_points_and_level()` - 手動調整積分

#### E. 管理功能
- `freeze_card()` / `unfreeze_card()` - 凍結/解凍卡片
- `admin_suspend_member()` / `admin_activate_member()` - 暫停/恢復會員
- `admin_suspend_merchant()` / `admin_activate_merchant()` - 暫停/恢復商戶
- `create_corporate_card()` - 創建企業折扣卡
- `create_voucher_card()` - 創建優惠券卡
- `set_card_binding_password()` - 設置卡片綁定密碼

#### F. 查詢功能
- `generate_settlement()` - 生成結算
- `list_settlements()` - 查詢結算列表
- `get_member_transactions()` - 會員交易記錄
- `get_merchant_transactions()` - 商戶交易記錄
- `get_transaction_detail()` - 交易詳情

---

## 🎭 三個主要角色的 UI 設計

### 👤 角色 1: 會員用戶 (Member App)

```
┌─────────────────────────────────────┐
│           MPS 會員系統              │
│      會員：張小明 (M00000001)      │
├─────────────────────────────────────┤
│ 1. 查看我的卡片                     │
│ 2. 生成付款 QR 碼                   │
│ 3. 充值卡片                         │
│ 4. 查看交易記錄                     │
│ 5. 綁定企業卡                       │
│ 6. 查看積分等級                     │
│ 7. 修改密碼                         │
│ 8. 登出系統                         │
└─────────────────────────────────────┘
```

**對應 RPC 功能**:
- 登入 → `member_login(p_identifier, p_password)`
- 查看卡片 → `get_member_cards(p_member_id)` 或查詢 `member_cards` 表
- 生成 QR 碼 → `rotate_card_qr(p_card_id, p_ttl_seconds, p_session_id)`
- 充值卡片 → `user_recharge_card(p_card_id, p_amount, ..., p_session_id)`
- 交易記錄 → `get_member_transactions(p_member_id, ..., p_session_id)`
- 綁定企業卡 → `bind_member_to_card(p_card_id, p_member_id, p_role, p_binding_password, p_session_id)`
- 修改密碼 → `set_member_password(p_member_id, p_password)`
- 登出 → `logout_session(p_session_id)`

### 🏪 角色 2: 商戶用戶 (Merchant POS)

```
┌─────────────────────────────────────┐
│           MPS 商戶 POS              │
│      商戶：星巴克 (SHOP001)       │
├─────────────────────────────────────┤
│ 1. 掃碼收款                         │
│ 2. 退款處理                         │
│ 3. 查看今日交易                     │
│ 4. 查看交易記錄                     │
│ 5. 生成結算報表                     │
│ 6. 查看結算歷史                     │
│ 7. 修改密碼                         │
│ 8. 登出系統                         │
└─────────────────────────────────────┘
```

**對應 RPC 功能**:
- 登入 → `merchant_login(p_merchant_code, p_password)`
- 掃碼收款 → `merchant_charge_by_qr(p_merchant_code, p_qr_plain, p_raw_amount, ..., p_session_id)`
- 退款處理 → `merchant_refund_tx(p_merchant_code, p_original_tx_no, p_refund_amount, ..., p_session_id)`
- 交易記錄 → `get_merchant_transactions(p_merchant_id, ..., p_session_id)`
- 結算報表 → `generate_settlement(p_merchant_id, p_mode, p_period_start, p_period_end)`
- 結算歷史 → `list_settlements(p_merchant_id, ..., p_session_id)`
- 修改密碼 → `set_merchant_password(p_merchant_id, p_password)` (需 Admin)
- 登出 → `logout_session(p_session_id)`

### 👨‍💼 角色 3: 平台管理員 (Admin Console)

```
┌─────────────────────────────────────┐
│          MPS 管理控制台             │
│         角色：Super Admin          │
├─────────────────────────────────────┤
│ 1. 會員管理                         │
│ 2. 商戶管理                         │
│ 3. 卡片管理                         │
│ 4. 交易監控                         │
│ 5. 系統維護                         │
│ 6. 數據報表                         │
│ 7. 認證管理                         │
│ 8. 登出系統                         │
└─────────────────────────────────────┘
```

**對應 RPC 功能**:
- 會員管理 → `create_member_profile()`, `admin_suspend_member()`, `admin_activate_member()`
- 商戶管理 → `create_merchant()`, `admin_suspend_merchant()`, `admin_activate_merchant()`
- 卡片管理 → `freeze_card()`, `unfreeze_card()`, `update_points_and_level()`, `create_corporate_card()`, `create_voucher_card()`
- 系統維護 → `cron_rotate_qr_tokens()`, `cleanup_expired_sessions()`
- 認證管理 → `set_member_password()`, `set_merchant_password()`, `set_card_binding_password()`

---

## 🏗️ Python CLI 應用架構

### 📁 項目結構
```
mps_cli/
├── main.py                 # 主入口
├── config/
│   ├── __init__.py
│   ├── settings.py         # 配置管理
│   └── supabase_client.py  # Supabase 客戶端
├── models/
│   ├── __init__.py
│   ├── member.py           # 會員模型
│   ├── card.py             # 卡片模型
│   ├── transaction.py      # 交易模型
│   └── merchant.py         # 商戶模型
├── services/
│   ├── __init__.py
│   ├── member_service.py   # 會員服務
│   ├── payment_service.py  # 支付服務
│   ├── merchant_service.py # 商戶服務
│   └── admin_service.py    # 管理服務
├── ui/
│   ├── __init__.py
│   ├── base_ui.py          # 基礎 UI 組件
│   ├── member_ui.py        # 會員界面
│   ├── merchant_ui.py      # 商戶界面
│   └── admin_ui.py         # 管理界面
├── utils/
│   ├── __init__.py
│   ├── helpers.py          # 工具函數
│   ├── validators.py       # 驗證器
│   └── formatters.py       # 格式化器
└── requirements.txt        # 依賴包
```

### 🎨 UI 設計原則

#### 1. 簡潔明瞭
- 使用 ASCII 字符繪製界面
- 清晰的菜單結構
- 直觀的操作流程

#### 2. 錯誤處理
- 友好的錯誤提示
- 輸入驗證
- 操作確認

#### 3. 數據展示
- 表格化數據顯示
- 分頁支持
- 搜索過濾

---

## 🔧 核心功能模組設計

### 📱 會員功能模組

#### 1. 我的卡片管理
```python
def show_my_cards(member_id: str):
    """顯示會員的所有卡片"""
    # 查詢會員卡片（需要直接查詢表，因為沒有對應 RPC）
    # 或者擴展一個 get_member_cards RPC
    
    cards = query_member_cards(member_id)
    
    print("┌─────────────────────────────────────────────────────────┐")
    print("│                    我的卡片                             │")
    print("├─────────────────────────────────────────────────────────┤")
    print("│ 卡號        │ 類型   │ 餘額     │ 積分   │ 等級   │ 狀態 │")
    print("├─────────────────────────────────────────────────────────┤")
    
    for card in cards:
        print(f"│ {card['card_no']:<10} │ {card['card_type']:<6} │ {card['balance']:>8.2f} │ {card['points']:>6} │ {card['level']:>6} │ {card['status']:<4} │")
    
    print("└─────────────────────────────────────────────────────────┘")
```

#### 2. 會員登入流程
```python
def member_login():
    """會員登入流程"""
    print("┌─────────────────────────────────────┐")
    print("│            會員系統登入             │")
    print("└─────────────────────────────────────┘")
    
    # 輸入識別符（手機或會員號）
    identifier = input("請輸入手機號碼或會員號: ")
    password = getpass.getpass("請輸入密碼: ")
    
    try:
        # 調用 member_login RPC
        result = rpc("member_login", {
            "p_identifier": identifier,
            "p_password": password
        })
        
        # 保存 session_id 用於後續調用
        session_id = result["session_id"]
        member_id = result["member_id"]
        member_name = result["name"]
        expires_at = result["expires_at"]
        
        print(f"✅ 登入成功！歡迎 {member_name}")
        print(f"Session 有效期至: {expires_at}")
        
        return session_id, member_id
        
    except Exception as e:
        if "MEMBER_NOT_FOUND" in str(e):
            print("❌ 會員不存在")
        elif "INVALID_PASSWORD" in str(e):
            print("❌ 密碼錯誤")
        elif "PASSWORD_NOT_SET" in str(e):
            print("❌ 尚未設置密碼，請聯繫管理員")
        else:
            print(f"❌ 登入失敗: {e}")
        return None, None
```

#### 3. 生成付款 QR 碼
```python
def generate_payment_qr(card_id: str, session_id: str):
    """生成付款 QR 碼"""
    try:
        # 調用 rotate_card_qr RPC
        # 注意：只有 Member 和 Super Admin 可以生成 QR，Merchant 不可以
        result = rpc("rotate_card_qr", {
            "p_card_id": card_id,
            "p_ttl_seconds": 900,  # 15分鐘
            "p_session_id": session_id  # 使用 session 認證
        })
        
        qr_plain = result[0]["qr_plain"]
        expires_at = result[0]["qr_expires_at"]
        
        print("┌─────────────────────────────────────┐")
        print("│            付款 QR 碼               │")
        print("├─────────────────────────────────────┤")
        print(f"│ QR 碼: {qr_plain:<25} │")
        print(f"│ 有效期: {expires_at:<23} │")
        print("├─────────────────────────────────────┤")
        print("│ 請向商戶出示此 QR 碼進行支付        │")
        print("└─────────────────────────────────────┘")
        
        return qr_plain
        
    except Exception as e:
        if "PERMISSION_DENIED" in str(e):
            print("❌ 沒有權限生成 QR 碼")
        elif "CARD_NOT_FOUND" in str(e):
            print("❌ 卡片不存在或未激活")
        else:
            print(f"❌ QR 碼生成失敗: {e}")
        return None
```

#### 4. 卡片充值（只支持 Standard Card）
```python
def recharge_card(card_id: str, session_id: str):
    """卡片充值（只支持 Standard Card）"""
    print("┌─────────────────────────────────────┐")
    print("│              卡片充值               │")
    print("│     （只支持標準卡充值）            │")
    print("└─────────────────────────────────────┘")
    
    # 輸入充值金額
    while True:
        try:
            amount = float(input("請輸入充值金額: "))
            if amount <= 0:
                print("❌ 充值金額必須大於 0")
                continue
            break
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    # 選擇支付方式
    payment_methods = ["wechat", "alipay", "bank"]
    print("\n支付方式:")
    for i, method in enumerate(payment_methods, 1):
        print(f"{i}. {method}")
    
    while True:
        try:
            choice = int(input("請選擇支付方式 (1-3): "))
            if 1 <= choice <= 3:
                payment_method = payment_methods[choice - 1]
                break
            print("❌ 請選擇 1-3")
        except ValueError:
            print("❌ 請輸入有效數字")
    
    # 生成冪等鍵
    import uuid
    idempotency_key = f"recharge-{uuid.uuid4()}"
    
    try:
        # 調用 user_recharge_card RPC
        result = rpc("user_recharge_card", {
            "p_card_id": card_id,
            "p_amount": amount,
            "p_payment_method": payment_method,
            "p_idempotency_key": idempotency_key,
            "p_tag": {"source": "cli_app"},
            "p_session_id": session_id  # 使用 session 認證
        })
        
        tx_no = result[0]["tx_no"]
        print(f"✅ 充值成功！交易號: {tx_no}")
        
    except Exception as e:
        if "UNSUPPORTED_CARD_TYPE_FOR_RECHARGE" in str(e):
            print("❌ 此卡片類型不支持充值（只有標準卡可以充值）")
        elif "CARD_NOT_FOUND_OR_INACTIVE" in str(e):
            print("❌ 卡片不存在或未激活")
        else:
            print(f"❌ 充值失敗: {e}")
```

### 🏪 商戶功能模組

#### 1. 商戶登入流程
```python
def merchant_login():
    """商戶登入流程"""
    print("┌─────────────────────────────────────┐")
    print("│            商戶系統登入             │")
    print("└─────────────────────────────────────┘")
    
    # 輸入商戶代碼和密碼
    merchant_code = input("請輸入商戶代碼: ")
    password = getpass.getpass("請輸入密碼: ")
    
    try:
        # 調用 merchant_login RPC
        result = rpc("merchant_login", {
            "p_merchant_code": merchant_code,
            "p_password": password
        })
        
        # 保存 session_id 用於後續調用
        session_id = result["session_id"]
        merchant_id = result["merchant_id"]
        merchant_name = result["merchant_name"]
        expires_at = result["expires_at"]
        
        print(f"✅ 登入成功！商戶: {merchant_name}")
        print(f"Session 有效期至: {expires_at}")
        
        return session_id, merchant_id, merchant_code
        
    except Exception as e:
        if "MERCHANT_NOT_FOUND" in str(e):
            print("❌ 商戶不存在")
        elif "INVALID_PASSWORD" in str(e):
            print("❌ 密碼錯誤")
        elif "PASSWORD_NOT_SET" in str(e):
            print("❌ 尚未設置密碼，請聯繫管理員")
        else:
            print(f"❌ 登入失敗: {e}")
        return None, None, None
```

#### 2. 掃碼收款
```python
def scan_and_charge(merchant_code: str, session_id: str):
    """掃碼收款流程"""
    print("┌─────────────────────────────────────┐")
    print("│              掃碼收款               │")
    print("└─────────────────────────────────────┘")
    
    # 模擬掃描 QR 碼（實際應用中會調用攝像頭）
    qr_plain = input("請輸入掃描到的 QR 碼: ")
    
    # 輸入金額
    while True:
        try:
            amount = float(input("請輸入收款金額: "))
            if amount <= 0:
                print("❌ 金額必須大於 0")
                continue
            break
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    # 確認收款
    print(f"\n收款信息確認:")
    print(f"金額: ¥{amount:.2f}")
    confirm = input("確認收款？(y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ 收款已取消")
        return
    
    # 生成冪等鍵
    import uuid
    idempotency_key = f"payment-{uuid.uuid4()}"
    
    try:
        # 調用 merchant_charge_by_qr RPC
        result = rpc("merchant_charge_by_qr", {
            "p_merchant_code": merchant_code,
            "p_qr_plain": qr_plain,
            "p_raw_amount": amount,
            "p_idempotency_key": idempotency_key,
            "p_tag": {"source": "pos_cli"},
            "p_external_order_id": f"CLI-{uuid.uuid4()}",
            "p_session_id": session_id  # 使用 session 認證
        })
        
        tx_id = result[0]["tx_id"]
        tx_no = result[0]["tx_no"]
        final_amount = result[0]["final_amount"]
        discount = result[0]["discount"]
        
        print("┌─────────────────────────────────────┐")
        print("│              收款成功               │")
        print("├─────────────────────────────────────┤")
        print(f"│ 交易號: {tx_no:<23} │")
        print(f"│ 原金額: ¥{amount:>25.2f} │")
        print(f"│ 折扣率: {discount:>26.1%} │")
        print(f"│ 實收金額: ¥{final_amount:>23.2f} │")
        print("└─────────────────────────────────────┘")
        
    except Exception as e:
        error_msg = str(e)
        if "INSUFFICIENT_BALANCE" in error_msg:
            print("❌ 客戶餘額不足，請提醒充值")
        elif "QR_EXPIRED_OR_INVALID" in error_msg:
            print("❌ QR 碼已過期，請客戶重新生成")
        elif "NOT_AUTHORIZED_FOR_THIS_MERCHANT" in error_msg:
            print("❌ 您沒有此商戶的操作權限")
        elif "CORPORATE_CARD_CANNOT_PAY" in error_msg:
            print("❌ 企業折扣卡不能直接支付（請使用標準卡）")
        elif "CARD_NOT_ACTIVE" in error_msg:
            print("❌ 卡片未激活")
        else:
            print(f"❌ 收款失敗: {error_msg}")
```

#### 3. 退款處理（支持多次部分退款）
```python
def process_refund(merchant_code: str, session_id: str):
    """退款處理流程（支持多次部分退款）"""
    print("┌─────────────────────────────────────┐")
    print("│              退款處理               │")
    print("│      （支持多次部分退款）           │")
    print("└─────────────────────────────────────┘")
    
    # 輸入原交易號
    original_tx_no = input("請輸入原交易號: ")
    
    # 查詢原交易詳情
    try:
        original_tx = rpc("get_transaction_detail", {
            "p_tx_no": original_tx_no
        })
        
        print(f"\n原交易信息:")
        print(f"交易號: {original_tx['tx_no']}")
        print(f"金額: ¥{original_tx['final_amount']:.2f}")
        print(f"狀態: {original_tx['status']}")
        print(f"時間: {original_tx['created_at']}")
        
    except Exception as e:
        print(f"❌ 查詢原交易失敗: {e}")
        return
    
    # 輸入退款金額
    while True:
        try:
            refund_amount = float(input("請輸入退款金額: "))
            if refund_amount <= 0:
                print("❌ 退款金額必須大於 0")
                continue
            if refund_amount > original_tx['final_amount']:
                print("❌ 退款金額不能超過原交易金額")
                continue
            break
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    # 退款原因
    reason = input("請輸入退款原因 (可選): ")
    
    # 確認退款
    print(f"\n退款信息確認:")
    print(f"原交易號: {original_tx_no}")
    print(f"退款金額: ¥{refund_amount:.2f}")
    print(f"退款原因: {reason or '無'}")
    confirm = input("確認退款？(y/n): ")
    
    if confirm.lower() != 'y':
        print("❌ 退款已取消")
        return
    
    try:
        # 調用 merchant_refund_tx RPC
        result = rpc("merchant_refund_tx", {
            "p_merchant_code": merchant_code,
            "p_original_tx_no": original_tx_no,
            "p_refund_amount": refund_amount,
            "p_tag": {"reason": reason, "source": "pos_cli"},
            "p_session_id": session_id  # 使用 session 認證
        })
        
        refund_tx_no = result[0]["refund_tx_no"]
        refunded_amount = result[0]["refunded_amount"]
        
        print("┌─────────────────────────────────────┐")
        print("│              退款成功               │")
        print("├─────────────────────────────────────┤")
        print(f"│ 退款單號: {refund_tx_no:<21} │")
        print(f"│ 退款金額: ¥{refunded_amount:>23.2f} │")
        print("└─────────────────────────────────────┘")
        
    except Exception as e:
        error_msg = str(e)
        if "REFUND_EXCEEDS_REMAINING" in error_msg:
            print("❌ 退款金額超過剩餘可退金額")
        elif "ONLY_COMPLETED_PAYMENT_REFUNDABLE" in error_msg:
            print("❌ 只能退款已完成的支付交易")
        elif "ORIGINAL_TX_NOT_FOUND" in error_msg:
            print("❌ 原交易不存在")
        elif "NOT_AUTHORIZED_FOR_THIS_MERCHANT" in error_msg:
            print("❌ 您沒有此商戶的操作權限")
        else:
            print(f"❌ 退款失敗: {error_msg}")
```

### 👨‍💼 管理員功能模組

#### 1. 會員管理
```python
def member_management():
    """會員管理功能"""
    while True:
        print("┌─────────────────────────────────────┐")
        print("│              會員管理               │")
        print("├─────────────────────────────────────┤")
        print("│ 1. 創建新會員                       │")
        print("│ 2. 查看會員信息                     │")
        print("│ 3. 暫停會員                         │")
        print("│ 4. 恢復會員                         │")
        print("│ 5. 返回主菜單                       │")
        print("└─────────────────────────────────────┘")
        
        choice = input("請選擇操作 (1-5): ")
        
        if choice == "1":
            create_new_member()
        elif choice == "2":
            view_member_info()
        elif choice == "3":
            suspend_member()
        elif choice == "4":
            restore_member()
        elif choice == "5":
            break
        else:
            print("❌ 無效選擇，請重新輸入")

def create_new_member():
    """創建新會員"""
    print("\n=== 創建新會員 ===")
    
    name = input("會員姓名: ")
    phone = input("手機號碼: ")
    email = input("電子郵件: ")
    
    # 可選的外部身份綁定
    bind_external = input("是否綁定外部身份？(y/n): ")
    binding_user_org = None
    binding_org_id = None
    
    if bind_external.lower() == 'y':
        binding_user_org = input("外部平台 (wechat/alipay/line): ")
        binding_org_id = input("外部用戶 ID: ")
    
    try:
        # 調用 create_member_profile RPC
        member_id = rpc("create_member_profile", {
            "p_name": name,
            "p_phone": phone,
            "p_email": email,
            "p_binding_user_org": binding_user_org,
            "p_binding_org_id": binding_org_id,
            "p_default_card_type": "standard"
        })
        
        print(f"✅ 會員創建成功！會員 ID: {member_id}")
        print("📋 已自動生成標準卡並綁定為 owner")
        
    except Exception as e:
        if "EXTERNAL_ID_ALREADY_BOUND" in str(e):
            print("❌ 外部身份已被其他會員綁定")
        else:
            print(f"❌ 會員創建失敗: {e}")
```

#### 2. 卡片管理
```python
def card_management():
    """卡片管理功能"""
    while True:
        print("┌─────────────────────────────────────┐")
        print("│              卡片管理               │")
        print("├─────────────────────────────────────┤")
        print("│ 1. 凍結卡片                         │")
        print("│ 2. 解凍卡片                         │")
        print("│ 3. 調整積分                         │")
        print("│ 4. 批量輪換 QR 碼                   │")
        print("│ 5. 返回主菜單                       │")
        print("└─────────────────────────────────────┘")
        
        choice = input("請選擇操作 (1-5): ")
        
        if choice == "1":
            freeze_card_ui()
        elif choice == "2":
            unfreeze_card_ui()
        elif choice == "3":
            adjust_points_ui()
        elif choice == "4":
            batch_rotate_qr_ui()
        elif choice == "5":
            break
        else:
            print("❌ 無效選擇，請重新輸入")

def freeze_card_ui():
    """凍結卡片界面"""
    card_id = input("請輸入要凍結的卡片 ID: ")
    
    confirm = input(f"確認凍結卡片 {card_id}？(y/n): ")
    if confirm.lower() != 'y':
        print("❌ 操作已取消")
        return
    
    try:
        # 調用 freeze_card RPC
        result = rpc("freeze_card", {"p_card_id": card_id})
        if result:
            print("✅ 卡片凍結成功")
        else:
            print("❌ 卡片凍結失敗")
    except Exception as e:
        print(f"❌ 凍結失敗: {e}")

def adjust_points_ui():
    """調整積分界面"""
    card_id = input("請輸入卡片 ID: ")
    
    while True:
        try:
            delta_points = int(input("請輸入積分變化量 (正數增加，負數減少): "))
            break
        except ValueError:
            print("❌ 請輸入有效的整數")
    
    reason = input("請輸入調整原因: ")
    
    try:
        # 調用 update_points_and_level RPC
        result = rpc("update_points_and_level", {
            "p_card_id": card_id,
            "p_delta_points": delta_points,
            "p_reason": reason
        })
        
        if result:
            print("✅ 積分調整成功")
        else:
            print("❌ 積分調整失敗")
            
    except Exception as e:
        print(f"❌ 調整失敗: {e}")
```

---

## 🎯 實現優先級

### 第一階段：核心功能 (MVP)
1. **會員 UI**: 查看卡片、生成 QR 碼、充值
2. **商戶 UI**: 掃碼收款、簡單退款
3. **管理員 UI**: 基本會員管理、卡片凍結

### 第二階段：完整功能
1. **交易查詢**: 各角色的交易記錄查詢
2. **結算功能**: 商戶結算生成和查詢
3. **高級管理**: 批量操作、數據報表

### 第三階段：增強功能
1. **數據可視化**: 簡單的 ASCII 圖表
2. **批量操作**: 批量 QR 輪換、批量結算
3. **系統監控**: 基本的系統狀態檢查

---

## 🛠️ 技術實現要點

### 1. 基礎架構
```python
# config/supabase_client.py
from supabase import create_client, Client
import os

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.client: Client = create_client(self.url, self.key)
    
    def rpc(self, function_name: str, params: dict):
        """調用 RPC 函數"""
        try:
            response = self.client.rpc(function_name, params).execute()
            return getattr(response, "data", response)
        except Exception as e:
            raise Exception(f"RPC call failed: {e}")
```

### 2. UI 基礎組件
```python
# ui/base_ui.py
class BaseUI:
    @staticmethod
    def clear_screen():
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def show_header(title: str):
        """顯示標題"""
        print("┌" + "─" * (len(title) + 2) + "┐")
        print(f"│ {title} │")
        print("└" + "─" * (len(title) + 2) + "┘")
    
    @staticmethod
    def show_menu(options: list) -> int:
        """顯示菜單並獲取選擇"""
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        while True:
            try:
                choice = int(input(f"請選擇 (1-{len(options)}): "))
                if 1 <= choice <= len(options):
                    return choice
                print(f"❌ 請選擇 1-{len(options)}")
            except ValueError:
                print("❌ 請輸入有效數字")
    
    @staticmethod
    def confirm_action(message: str) -> bool:
        """確認操作"""
        response = input(f"{message} (y/n): ")
        return response.lower() == 'y'
```

### 3. 錯誤處理
```python
# utils/error_handler.py
class ErrorHandler:
    ERROR_MESSAGES = {
        "INSUFFICIENT_BALANCE": "餘額不足，請充值後再試",
        "QR_EXPIRED_OR_INVALID": "QR 碼已過期或無效，請重新生成",
        "MERCHANT_NOT_FOUND_OR_INACTIVE": "商戶不存在或已停用",
        "NOT_MERCHANT_USER": "您沒有此商戶的操作權限",
        "CARD_NOT_FOUND_OR_INACTIVE": "卡片不存在或未激活",
        "EXTERNAL_ID_ALREADY_BOUND": "外部身份已被其他會員綁定",
        "INVALID_BINDING_PASSWORD": "綁定密碼錯誤",
        "REFUND_EXCEEDS_REMAINING": "退款金額超過可退金額"
    }
    
    @classmethod
    def handle_rpc_error(cls, error: Exception) -> str:
        """處理 RPC 錯誤"""
        error_str = str(error)
        
        for code, message in cls.ERROR_MESSAGES.items():
            if code in error_str:
                return f"❌ {message}"
        
        return f"❌ 操作失敗: {error_str}"
```

---

## 📋 功能清單與流程

### 🎯 會員端功能清單
| 功能 | 對應 RPC | 實現難度 | 優先級 |
|------|----------|----------|--------|
| 查看卡片列表 | 直接查詢表 | 簡單 | 高 |
| 生成付款 QR | `rotate_card_qr` | 簡單 | 高 |
| 卡片充值 | `user_recharge_card` | 中等 | 高 |
| 查看交易記錄 | `get_member_transactions` | 簡單 | 中 |
| 綁定共享卡 | `bind_member_to_card` | 中等 | 中 |
| 查看積分等級 | 直接查詢表 | 簡單 | 低 |

### 🏪 商戶端功能清單
| 功能 | 對應 RPC | 實現難度 | 優先級 |
|------|----------|----------|--------|
| 掃碼收款 | `merchant_charge_by_qr` | 中等 | 高 |
| 退款處理 | `merchant_refund_tx` | 中等 | 高 |
| 查看交易記錄 | `get_merchant_transactions` | 簡單 | 中 |
| 交易詳情查詢 | `get_transaction_detail` | 簡單 | 中 |
| 生成結算 | `generate_settlement` | 簡單 | 中 |
| 查看結算歷史 | `list_settlements` | 簡單 | 低 |

### 👨‍💼 管理員功能清單
| 功能 | 對應 RPC | 實現難度 | 優先級 |
|------|----------|----------|--------|
| 創建會員 | `create_member_profile` | 簡單 | 高 |
| 凍結/解凍卡片 | `freeze_card`, `unfreeze_card` | 簡單 | 高 |
| 暫停會員 | `admin_suspend_member` | 簡單 | 中 |
| 暫停商戶 | `admin_suspend_merchant` | 簡單 | 中 |
| 調整積分 | `update_points_and_level` | 簡單 | 中 |
| 批量 QR 輪換 | `cron_rotate_qr_tokens` | 簡單 | 低 |

---

## 🚀 開發建議

### 1. 技術棧
- **Python 3.8+**
- **supabase-py** - Supabase 客戶端
- **rich** - 美化終端輸出（可選）
- **click** - 命令行參數處理（可選）

### 2. 開發順序
1. 先實現基礎的 Supabase 連接和 RPC 調用
2. 創建簡單的文字菜單系統
3. 實現核心業務流程（支付、充值、退款）
4. 添加數據查詢和展示功能
5. 完善錯誤處理和用戶體驗

### 3. 測試策略
- 使用測試數據庫進行開發測試
- 創建模擬數據進行功能驗證
- 重點測試錯誤處理和邊界情況

這個設計完全基於現有的 RPC 功能，不會超出當前系統範疇，同時提供了實用的文字 UI 界面來操作 MPS 系統的核心功能。