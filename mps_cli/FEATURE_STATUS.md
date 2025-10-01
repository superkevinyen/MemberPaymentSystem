# MPS CLI 功能實現狀態

> 追蹤所有功能的實現進度和質量

## 📊 總體進度

| 模塊 | 完成度 | 狀態 | 優先級 |
|------|--------|------|--------|
| **會員端** | 40% | 🚧 進行中 | P0 |
| **商戶端** | 50% | 🚧 進行中 | P0 |
| **管理端** | 30% | 🚧 進行中 | P1 |
| **基礎設施** | 80% | ✅ 基本完成 | P0 |
| **測試** | 20% | ❌ 待開始 | P1 |
| **文檔** | 30% | 🚧 進行中 | P2 |

**總體完成度**: **45%**

---

## 👤 會員端功能 (Member UI)

### 核心功能

| # | 功能 | RPC 函數 | 狀態 | 完成度 | 優先級 | 負責人 | 備註 |
|---|------|----------|------|--------|--------|--------|------|
| 1.1 | 會員登入 | `member_login` | ✅ 完成 | 100% | P0 | - | 在 LoginUI 中實現 |
| 1.2 | 查看我的卡片 | 查詢 `member_cards` | ✅ 完成 | 90% | P0 | - | 需優化顯示 |
| 1.3 | 生成付款 QR 碼 | `rotate_card_qr` | 🚧 進行中 | 60% | P0 | - | 需完善流程 |
| 1.4 | 充值卡片 | `user_recharge_card` | 🚧 進行中 | 50% | P0 | - | 需完善流程 |
| 1.5 | 查看交易記錄 | `get_member_transactions` | 🚧 進行中 | 40% | P0 | - | 需實現分頁 |
| 1.6 | 綁定企業卡 | `bind_member_to_card` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 1.7 | 查看積分等級 | 查詢 `member_cards` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 1.8 | 修改密碼 | `set_member_password` | ❌ 未開始 | 0% | P2 | - | 待實現 |
| 1.9 | 登出系統 | `logout_session` | ✅ 完成 | 100% | P0 | - | 在 AuthService 中實現 |

### 詳細狀態

#### 1.2 查看我的卡片 ✅ 90%
**已實現**：
- ✅ 獲取卡片列表
- ✅ 表格顯示卡片信息
- ✅ 顯示卡號、類型、餘額、積分、等級、狀態

**待優化**：
- [ ] 顯示綁定關係（owner/member/viewer）
- [ ] 顯示企業折扣信息
- [ ] 支持卡片詳情查看
- [ ] 支持卡片切換選擇

**文件位置**: `ui/member_ui.py::_show_my_cards()`

---

#### 1.3 生成付款 QR 碼 🚧 60%
**已實現**：
- ✅ 選擇卡片
- ✅ 調用 `rotate_card_qr` RPC
- ✅ 顯示 QR 碼

**待實現**：
- [ ] 卡片類型檢查（Corporate Card 不能生成 QR）
- [ ] 顯示過期時間倒計時
- [ ] 支持刷新 QR 碼
- [ ] 支持撤銷 QR 碼
- [ ] 顯示 QR 碼使用說明

**文件位置**: `ui/member_ui.py::_generate_qr()`

**實現建議**：
```python
def _generate_qr(self):
    # 1. 獲取卡片列表
    cards = self._get_available_cards_for_qr()  # 過濾掉 Corporate Card
    
    # 2. 選擇卡片
    card = self._select_card(cards)
    
    # 3. 檢查卡片狀態
    if card.status != 'active':
        BaseUI.show_error("Card is not active")
        return
    
    # 4. 生成 QR 碼
    qr_result = self.qr_service.generate_qr(card.id, ttl_seconds=900)
    
    # 5. 顯示 QR 碼（帶倒計時）
    self._display_qr_with_countdown(qr_result)
    
    # 6. 提供操作選項（刷新/撤銷/返回）
    self._qr_action_menu(card.id)
```

---

#### 1.4 充值卡片 🚧 50%
**已實現**：
- ✅ 選擇卡片
- ✅ 輸入金額
- ✅ 調用 `user_recharge_card` RPC

**待實現**：
- [ ] 卡片類型檢查（只有 Standard Card 可充值）
- [ ] 支付方式選擇（wechat/alipay/cash/balance）
- [ ] 顯示充值確認信息
- [ ] 顯示充值結果（交易號）
- [ ] 錯誤處理優化

**文件位置**: `ui/member_ui.py::_recharge_card()`

**實現建議**：
```python
def _recharge_card(self):
    # 1. 獲取可充值卡片（只有 Standard Card）
    cards = self._get_rechargeable_cards()
    
    if not cards:
        BaseUI.show_info("No rechargeable cards (only Standard Card can be recharged)")
        return
    
    # 2. 選擇卡片
    card = self._select_card(cards)
    
    # 3. 輸入金額
    amount = QuickForm.get_amount("Enter recharge amount", 1, 10000)
    
    # 4. 選擇支付方式
    payment_method = self._select_payment_method()
    
    # 5. 顯示確認信息
    if not self._confirm_recharge(card, amount, payment_method):
        return
    
    # 6. 執行充值
    result = self.payment_service.recharge_card(
        card.id, amount, payment_method
    )
    
    # 7. 顯示結果
    self._display_recharge_result(result)
```

---

#### 1.5 查看交易記錄 🚧 40%
**已實現**：
- ✅ 獲取交易列表
- ✅ 表格顯示

**待實現**：
- [ ] 分頁顯示
- [ ] 日期範圍篩選
- [ ] 交易類型篩選（payment/refund/recharge）
- [ ] 交易狀態篩選
- [ ] 查看交易詳情
- [ ] 導出功能（可選）

**文件位置**: `ui/member_ui.py::_view_transactions()`

---

#### 1.6 綁定企業卡 ❌ 0%
**需實現**：
- [ ] 輸入企業卡 ID
- [ ] 輸入綁定密碼
- [ ] 選擇綁定角色（member/viewer）
- [ ] 調用 `bind_member_to_card` RPC
- [ ] 顯示綁定結果
- [ ] 顯示企業折扣信息
- [ ] 錯誤處理（密碼錯誤、卡片不存在等）

**文件位置**: `ui/member_ui.py::_bind_new_card()` (待實現)

**實現建議**：
```python
def _bind_new_card(self):
    BaseUI.show_header("Bind Corporate Card")
    
    # 1. 輸入企業卡 ID
    card_id = input("Enter Corporate Card ID: ").strip()
    
    # 2. 選擇綁定角色
    role = self._select_binding_role()  # member or viewer
    
    # 3. 輸入綁定密碼
    password = QuickForm.get_password("Enter binding password")
    
    # 4. 顯示確認信息
    if not BaseUI.confirm(f"Bind to card {card_id} as {role}?"):
        return
    
    # 5. 執行綁定
    try:
        result = self.member_service.bind_to_card(
            card_id, self.current_member_id, role, password
        )
        
        # 6. 顯示結果
        BaseUI.show_success("Card bound successfully!")
        if result.get('corporate_discount'):
            BaseUI.show_info(
                f"Corporate discount: {result['corporate_discount']*100}%"
            )
            
    except Exception as e:
        self._handle_binding_error(e)
```

---

#### 1.7 查看積分等級 ❌ 0%
**需實現**：
- [ ] 獲取卡片積分信息
- [ ] 顯示當前積分
- [ ] 顯示當前等級
- [ ] 顯示當前折扣
- [ ] 顯示升級進度（距離下一等級）
- [ ] 顯示積分歷史（可選）

**文件位置**: `ui/member_ui.py::_view_points_level()` (待實現)

**實現建議**：
```python
def _view_points_level(self):
    BaseUI.show_header("Points & Level")
    
    # 1. 獲取卡片列表
    cards = self.member_service.get_member_cards(self.current_member_id)
    
    # 2. 顯示每張卡的積分信息
    for card in cards:
        if card.card_type == 'standard':  # 只有標準卡有積分
            self._display_card_points_info(card)
    
    BaseUI.pause()

def _display_card_points_info(self, card):
    print(f"\n{card.card_no} - {card.get_card_type_display()}")
    print("─" * 40)
    print(f"Current Points: {card.points:,}")
    print(f"Current Level: {card.get_level_display()}")
    print(f"Current Discount: {card.discount*100:.1f}%")
    
    # 計算升級進度
    next_level_points = self._get_next_level_points(card.level)
    if next_level_points:
        progress = (card.points / next_level_points) * 100
        print(f"Upgrade Progress: {progress:.1f}%")
        print(f"Points needed: {next_level_points - card.points:,}")
```

---

## 🏪 商戶端功能 (Merchant UI)

### 核心功能

| # | 功能 | RPC 函數 | 狀態 | 完成度 | 優先級 | 負責人 | 備註 |
|---|------|----------|------|--------|--------|--------|------|
| 2.1 | 商戶登入 | `merchant_login` | ✅ 完成 | 100% | P0 | - | 在 LoginUI 中實現 |
| 2.2 | 掃碼收款 | `merchant_charge_by_qr` | ✅ 完成 | 85% | P0 | - | 需優化錯誤提示 |
| 2.3 | 退款處理 | `merchant_refund_tx` | 🚧 進行中 | 60% | P0 | - | 需完善流程 |
| 2.4 | 查看今日交易 | `get_merchant_transactions` | 🚧 進行中 | 50% | P0 | - | 需實現統計 |
| 2.5 | 查看交易記錄 | `get_merchant_transactions` | 🚧 進行中 | 40% | P0 | - | 需實現分頁 |
| 2.6 | 生成結算報表 | `generate_settlement` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 2.7 | 查看結算歷史 | `list_settlements` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 2.8 | 修改密碼 | `set_merchant_password` | ❌ 未開始 | 0% | P2 | - | 需 Admin 權限 |
| 2.9 | 登出系統 | `logout_session` | ✅ 完成 | 100% | P0 | - | 在 AuthService 中實現 |

### 詳細狀態

#### 2.2 掃碼收款 ✅ 85%
**已實現**：
- ✅ QR 碼輸入
- ✅ QR 碼驗證
- ✅ 金額輸入
- ✅ 收款確認
- ✅ 調用 `merchant_charge_by_qr` RPC
- ✅ 顯示收款結果

**待優化**：
- [ ] 增強錯誤提示
  - 餘額不足 → 提示客戶充值
  - QR 過期 → 提示重新掃碼
  - 企業卡錯誤 → 提示使用標準卡
  - 卡片未激活 → 明確提示
- [ ] 顯示折扣計算過程
- [ ] 打印收據選項（可選）
- [ ] 支持外部訂單號輸入

**文件位置**: `ui/merchant_ui.py::_scan_and_charge()`

---

#### 2.3 退款處理 🚧 60%
**已實現**：
- ✅ 輸入原交易號
- ✅ 查詢原交易
- ✅ 輸入退款金額
- ✅ 調用 `merchant_refund_tx` RPC

**待實現**：
- [ ] 顯示剩餘可退金額
- [ ] 支持多次部分退款
- [ ] 顯示退款歷史
- [ ] 退款原因輸入
- [ ] 錯誤處理優化

**文件位置**: `ui/merchant_ui.py::_process_refund()`

**實現建議**：
```python
def _process_refund(self):
    BaseUI.show_header("Process Refund")
    
    # 1. 輸入原交易號
    tx_no = input("Enter original transaction number: ").strip()
    
    # 2. 查詢原交易
    try:
        original_tx = self.payment_service.get_transaction_detail(tx_no)
    except Exception as e:
        BaseUI.show_error(f"Transaction not found: {e}")
        return
    
    # 3. 顯示原交易信息
    self._display_transaction_info(original_tx)
    
    # 4. 計算剩餘可退金額
    remaining = self._calculate_remaining_refundable(original_tx)
    print(f"\nRemaining refundable amount: {Formatter.format_currency(remaining)}")
    
    if remaining <= 0:
        BaseUI.show_error("No refundable amount remaining")
        return
    
    # 5. 輸入退款金額
    refund_amount = QuickForm.get_amount(
        "Enter refund amount", 0.01, float(remaining)
    )
    
    # 6. 輸入退款原因
    reason = input("Enter refund reason (optional): ").strip()
    
    # 7. 確認退款
    if not self._confirm_refund(original_tx, refund_amount, reason):
        return
    
    # 8. 執行退款
    result = self.payment_service.refund_transaction(
        self.current_merchant_code,
        tx_no,
        refund_amount,
        reason
    )
    
    # 9. 顯示結果
    self._display_refund_result(result)
```

---

#### 2.4 查看今日交易 🚧 50%
**已實現**：
- ✅ 獲取今日交易列表
- ✅ 表格顯示

**待實現**：
- [ ] 今日統計（筆數、金額、淨收入）
- [ ] 分類統計（支付、退款）
- [ ] 實時刷新選項
- [ ] 圖表顯示（可選）

**文件位置**: `ui/merchant_ui.py::_view_today_transactions()`

---

#### 2.6 生成結算報表 ❌ 0%
**需實現**：
- [ ] 選擇結算模式（realtime/t_plus_1/monthly）
- [ ] 選擇結算期間
- [ ] 調用 `generate_settlement` RPC
- [ ] 顯示結算詳情
- [ ] 導出報表（可選）

**文件位置**: `ui/merchant_ui.py::_generate_settlement()` (待實現)

---

#### 2.7 查看結算歷史 ❌ 0%
**需實現**：
- [ ] 獲取結算列表
- [ ] 分頁顯示
- [ ] 查看結算詳情
- [ ] 導出功能（可選）

**文件位置**: `ui/merchant_ui.py::_view_settlement_history()` (待實現)

---

## 👨‍💼 管理端功能 (Admin UI)

### 核心功能

| # | 功能 | RPC 函數 | 狀態 | 完成度 | 優先級 | 負責人 | 備註 |
|---|------|----------|------|--------|--------|--------|------|
| 3.1 | 管理員登入 | Supabase Auth | ✅ 完成 | 100% | P0 | - | 在 LoginUI 中實現 |
| 3.2 | 創建會員 | `create_member_profile` | ✅ 完成 | 80% | P0 | - | 需優化 |
| 3.3 | 管理會員 | 多個 RPC | 🚧 進行中 | 40% | P1 | - | 部分實現 |
| 3.4 | 創建商戶 | `create_merchant` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 3.5 | 管理商戶 | 多個 RPC | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 3.6 | 創建企業卡 | `create_corporate_card` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 3.7 | 創建優惠券卡 | `create_voucher_card` | ❌ 未開始 | 0% | P1 | - | 待實現 |
| 3.8 | 卡片管理 | 多個 RPC | 🚧 進行中 | 30% | P1 | - | 部分實現 |
| 3.9 | 交易監控 | 查詢 | ❌ 未開始 | 0% | P2 | - | 待實現 |
| 3.10 | 系統維護 | 多個 RPC | ❌ 未開始 | 0% | P2 | - | 待實現 |
| 3.11 | 數據報表 | 查詢 | ❌ 未開始 | 0% | P2 | - | 待實現 |

---

## 🏗️ 基礎設施

### Services 層

| 服務 | 完成度 | 狀態 | 備註 |
|------|--------|------|------|
| `AuthService` | 90% | ✅ 基本完成 | 需完善 Session 刷新 |
| `MemberService` | 70% | 🚧 進行中 | 需補充查詢方法 |
| `MerchantService` | 60% | 🚧 進行中 | 需補充結算方法 |
| `PaymentService` | 80% | ✅ 基本完成 | 需優化錯誤處理 |
| `QRService` | 85% | ✅ 基本完成 | 功能完整 |
| `AdminService` | 50% | 🚧 進行中 | 需補充管理方法 |

### UI 組件

| 組件 | 完成度 | 狀態 | 備註 |
|------|--------|------|------|
| `Menu` | 95% | ✅ 完成 | 功能完整 |
| `Table` | 85% | ✅ 基本完成 | 需優化對齊 |
| `PaginatedTable` | 70% | 🚧 進行中 | 需完善分頁 |
| `Form` | 80% | ✅ 基本完成 | 需補充驗證 |
| `QuickForm` | 90% | ✅ 完成 | 功能完整 |

### Utils 工具

| 工具 | 完成度 | 狀態 | 備註 |
|------|--------|------|------|
| `Validator` | 85% | ✅ 基本完成 | 需補充業務驗證 |
| `Formatter` | 90% | ✅ 完成 | 功能完整 |
| `Logger` | 95% | ✅ 完成 | 功能完整 |
| `ErrorHandler` | 70% | 🚧 進行中 | 需完善錯誤映射 |

---

## 🧪 測試覆蓋

| 測試類型 | 覆蓋率 | 狀態 | 目標 |
|----------|--------|------|------|
| 單元測試 | 20% | ❌ 待開始 | 80% |
| 集成測試 | 15% | ❌ 待開始 | 60% |
| E2E 測試 | 10% | ❌ 待開始 | 40% |

---

## 📚 文檔狀態

| 文檔類型 | 完成度 | 狀態 | 備註 |
|----------|--------|------|------|
| README | 60% | 🚧 進行中 | 需更新 |
| API 文檔 | 30% | 🚧 進行中 | 需補充 |
| 用戶手冊 | 20% | ❌ 待開始 | 待編寫 |
| 開發文檔 | 40% | 🚧 進行中 | 需補充 |

---

## 🎯 下一步優先級

### 本週必須完成 (P0)
1. ✅ 會員端：生成 QR 碼完善
2. ✅ 會員端：充值流程完善
3. ✅ 商戶端：退款流程完善
4. ✅ 商戶端：今日交易統計

### 下週計劃 (P1)
1. 會員端：綁定企業卡
2. 會員端：查看積分等級
3. 商戶端：結算功能
4. 管理端：核心功能補全

---

**最後更新**: 2025-10-01  
**更新人**: System  
**下次更新**: 每日更新
