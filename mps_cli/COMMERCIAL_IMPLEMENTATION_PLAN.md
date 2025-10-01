# MPS CLI 商業化實施計劃

> 基於 docs 規範和測試代碼，打造專業、完整、易用的商業級產品

## 🎯 商業化標準

### 產品定位
- **目標用戶**: 會員、商戶、管理員
- **使用場景**: 日常運營、實際交易、數據管理
- **質量要求**: 穩定、安全、易用、專業

### 核心要求
1. **功能完整**: 100% 實現所有規格功能
2. **用戶體驗**: 清晰的界面、友好的提示、流暢的操作
3. **錯誤處理**: 詳細的錯誤信息、明確的解決方案
4. **數據準確**: 精確的計算、完整的驗證
5. **專業呈現**: 統一的風格、規範的格式

---

## 📋 實施路線圖

### Phase 1: 會員端完善 (Week 1-2)

#### 1.1 生成付款 QR 碼 - 完整實現

**參考**: `docs/python_ui_specification.md` Line 258-293  
**測試**: `tests/test_complete_business_flow.py` Line 94-99

**需求**:
```
1. 顯示所有可用卡片（排除 Corporate Card）
2. 卡片信息完整展示（卡號、類型、餘額、狀態）
3. 生成 QR 碼並顯示完整信息
4. 顯示過期時間和使用說明
5. 提供操作選項（刷新/撤銷/返回）
```

**實現代碼**:
```python
def _generate_qr(self):
    """生成付款 QR 碼 - 商業版"""
    try:
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║              生成付款 QR 碼                           ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        # Step 1: 獲取可用卡片（排除 Corporate Card）
        BaseUI.show_loading("正在獲取卡片信息...")
        all_cards = self.member_service.get_member_cards(self.current_member_id)
        
        # 過濾：只有 Standard 和 Voucher 可以生成 QR
        available_cards = [
            card for card in all_cards 
            if card.card_type in ['standard', 'voucher'] and card.status == 'active'
        ]
        
        if not available_cards:
            print("\n⚠️  沒有可用的卡片")
            print("   提示：")
            print("   • 標準卡和代金券卡可以生成 QR 碼")
            print("   • 企業折扣卡不能生成 QR 碼（只提供折扣）")
            print("   • 卡片必須處於激活狀態")
            BaseUI.pause()
            return
        
        # Step 2: 顯示卡片列表
        print("\n可用卡片：")
        print("─" * 80)
        print(f"{'序號':<4} {'卡號':<16} {'類型':<12} {'餘額':<12} {'積分':<8} {'狀態':<8}")
        print("─" * 80)
        
        for i, card in enumerate(available_cards, 1):
            print(f"{i:<4} {card.card_no:<16} {card.get_card_type_display():<12} "
                  f"{Formatter.format_currency(card.balance):<12} "
                  f"{card.points or 0:<8} {card.get_status_display():<8}")
        
        print("─" * 80)
        
        # Step 3: 選擇卡片
        while True:
            try:
                choice = input(f"\n請選擇卡片 (1-{len(available_cards)}) 或 q 返回: ").strip()
                if choice.lower() == 'q':
                    return
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_cards):
                    selected_card = available_cards[choice_num - 1]
                    break
                print(f"❌ 請輸入 1-{len(available_cards)}")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        # Step 4: 確認生成
        print(f"\n選中卡片：{selected_card.card_no} ({selected_card.get_card_type_display()})")
        print(f"當前餘額：{Formatter.format_currency(selected_card.balance)}")
        
        if not BaseUI.confirm("\n確認生成 QR 碼？"):
            print("❌ 已取消")
            BaseUI.pause()
            return
        
        # Step 5: 生成 QR 碼
        BaseUI.show_loading("正在生成 QR 碼...")
        qr_result = self.qr_service.rotate_qr(selected_card.id, ttl_seconds=900)
        
        # Step 6: 顯示 QR 碼
        BaseUI.clear_screen()
        self._display_qr_code(qr_result, selected_card)
        
        # Step 7: 操作菜單
        self._qr_action_menu(selected_card, qr_result)
        
    except Exception as e:
        BaseUI.show_error(f"生成 QR 碼失敗: {e}")
        self.logger.error(f"生成 QR 碼失敗: {e}", exc_info=True)
        BaseUI.pause()

def _display_qr_code(self, qr_result: Dict, card: Card):
    """顯示 QR 碼信息"""
    qr_plain = qr_result.get('qr_plain')
    expires_at = qr_result.get('expires_at')
    
    print("╔═══════════════════════════════════════════════════════╗")
    print("║                  付款 QR 碼                           ║")
    print("╠═══════════════════════════════════════════════════════╣")
    print(f"║  QR 碼: {qr_plain:<42} ║")
    print(f"║  卡號:  {card.card_no:<42} ║")
    print(f"║  類型:  {card.get_card_type_display():<42} ║")
    print(f"║  餘額:  {Formatter.format_currency(card.balance):<42} ║")
    print("╠═══════════════════════════════════════════════════════╣")
    print(f"║  有效期至: {expires_at:<39} ║")
    print(f"║  有效時長: 15 分鐘{'':>38} ║")
    print("╠═══════════════════════════════════════════════════════╣")
    print("║  使用說明：                                           ║")
    print("║  1. 請向商戶出示此 QR 碼                              ║")
    print("║  2. 商戶掃碼後輸入金額即可完成支付                    ║")
    print("║  3. QR 碼過期後需要重新生成                           ║")
    print("╚═══════════════════════════════════════════════════════╝")

def _qr_action_menu(self, card: Card, qr_result: Dict):
    """QR 碼操作菜單"""
    while True:
        print("\n操作選項：")
        print("  1. 刷新 QR 碼")
        print("  2. 撤銷 QR 碼")
        print("  3. 返回主菜單")
        
        choice = input("\n請選擇 (1-3): ").strip()
        
        if choice == '1':
            # 刷新 QR 碼
            if BaseUI.confirm("確認刷新 QR 碼？"):
                try:
                    BaseUI.show_loading("正在刷新...")
                    new_qr = self.qr_service.rotate_qr(card.id, ttl_seconds=900)
                    BaseUI.clear_screen()
                    self._display_qr_code(new_qr, card)
                    BaseUI.show_success("QR 碼已刷新")
                except Exception as e:
                    BaseUI.show_error(f"刷新失敗: {e}")
        
        elif choice == '2':
            # 撤銷 QR 碼
            if BaseUI.confirm("確認撤銷 QR 碼？撤銷後此 QR 碼將立即失效。"):
                try:
                    BaseUI.show_loading("正在撤銷...")
                    self.qr_service.revoke_qr(card.id)
                    BaseUI.show_success("QR 碼已撤銷")
                    BaseUI.pause()
                    return
                except Exception as e:
                    BaseUI.show_error(f"撤銷失敗: {e}")
        
        elif choice == '3':
            return
        
        else:
            print("❌ 請輸入 1-3")
```

**測試驗證**:
```bash
# 運行測試驗證 QR 生成流程
python tests/test_complete_business_flow.py
```

---

#### 1.2 充值卡片 - 完整實現

**參考**: `docs/python_ui_specification.md` Line 295-356  
**測試**: `tests/test_complete_business_flow.py` Line 72-85

**需求**:
```
1. 只允許 Standard Card 充值
2. 支持多種支付方式選擇
3. 顯示充值確認信息
4. 顯示充值結果和交易號
5. 完整的錯誤處理
```

**實現代碼**:
```python
def _recharge_card(self):
    """充值卡片 - 商業版（只支持 Standard Card）"""
    try:
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║                  卡片充值                             ║")
        print("║            （只支持標準卡充值）                       ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        # Step 1: 獲取可充值卡片（只有 Standard Card）
        BaseUI.show_loading("正在獲取卡片信息...")
        all_cards = self.member_service.get_member_cards(self.current_member_id)
        
        rechargeable_cards = [
            card for card in all_cards 
            if card.card_type == 'standard' and card.status == 'active'
        ]
        
        if not rechargeable_cards:
            print("\n⚠️  沒有可充值的卡片")
            print("   提示：")
            print("   • 只有標準卡支持充值")
            print("   • 企業折扣卡和代金券卡不可充值")
            print("   • 卡片必須處於激活狀態")
            BaseUI.pause()
            return
        
        # Step 2: 顯示卡片列表
        print("\n可充值卡片：")
        print("─" * 80)
        print(f"{'序號':<4} {'卡號':<16} {'當前餘額':<12} {'積分':<8} {'等級':<10}")
        print("─" * 80)
        
        for i, card in enumerate(rechargeable_cards, 1):
            print(f"{i:<4} {card.card_no:<16} "
                  f"{Formatter.format_currency(card.balance):<12} "
                  f"{card.points or 0:<8} {card.get_level_display():<10}")
        
        print("─" * 80)
        
        # Step 3: 選擇卡片
        while True:
            try:
                choice = input(f"\n請選擇卡片 (1-{len(rechargeable_cards)}) 或 q 返回: ").strip()
                if choice.lower() == 'q':
                    return
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(rechargeable_cards):
                    selected_card = rechargeable_cards[choice_num - 1]
                    break
                print(f"❌ 請輸入 1-{len(rechargeable_cards)}")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        # Step 4: 輸入充值金額
        print(f"\n選中卡片：{selected_card.card_no}")
        print(f"當前餘額：{Formatter.format_currency(selected_card.balance)}")
        
        while True:
            try:
                amount_str = input("\n請輸入充值金額 (1-50000): ").strip()
                amount = Decimal(amount_str)
                
                if amount < Decimal("1"):
                    print("❌ 充值金額不能小於 ¥1")
                    continue
                if amount > Decimal("50000"):
                    print("❌ 單次充值金額不能超過 ¥50,000")
                    continue
                
                break
            except (ValueError, InvalidOperation):
                print("❌ 請輸入有效的金額")
        
        # Step 5: 選擇支付方式
        payment_methods = [
            {"code": "wechat", "name": "微信支付", "icon": "💚"},
            {"code": "alipay", "name": "支付寶", "icon": "💙"},
            {"code": "bank", "name": "銀行卡", "icon": "💳"},
            {"code": "cash", "name": "現金", "icon": "💵"}
        ]
        
        print("\n支付方式：")
        for i, method in enumerate(payment_methods, 1):
            print(f"  {i}. {method['icon']} {method['name']}")
        
        while True:
            try:
                method_choice = int(input(f"\n請選擇支付方式 (1-{len(payment_methods)}): "))
                if 1 <= method_choice <= len(payment_methods):
                    selected_method = payment_methods[method_choice - 1]
                    break
                print(f"❌ 請輸入 1-{len(payment_methods)}")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        # Step 6: 確認充值
        print("\n" + "═" * 60)
        print("充值信息確認")
        print("═" * 60)
        print(f"卡號：        {selected_card.card_no}")
        print(f"當前餘額：    {Formatter.format_currency(selected_card.balance)}")
        print(f"充值金額：    {Formatter.format_currency(amount)}")
        print(f"充值後餘額：  {Formatter.format_currency(selected_card.balance + amount)}")
        print(f"支付方式：    {selected_method['icon']} {selected_method['name']}")
        print("═" * 60)
        
        if not BaseUI.confirm("\n確認充值？"):
            print("❌ 已取消充值")
            BaseUI.pause()
            return
        
        # Step 7: 執行充值
        BaseUI.show_loading("正在處理充值...")
        
        import uuid
        idempotency_key = f"recharge-{uuid.uuid4()}"
        
        result = self.payment_service.recharge_card(
            selected_card.id,
            amount,
            selected_method['code'],
            idempotency_key=idempotency_key
        )
        
        # Step 8: 顯示充值結果
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║                充值成功！                             ║")
        print("╠═══════════════════════════════════════════════════════╣")
        print(f"║  交易號：  {result['tx_no']:<39} ║")
        print(f"║  充值金額：{Formatter.format_currency(amount):<39} ║")
        print(f"║  支付方式：{selected_method['name']:<39} ║")
        print(f"║  處理時間：{Formatter.format_datetime(result.get('created_at')):<39} ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        print("\n✅ 充值已到賬，您可以開始使用了！")
        
        # 記錄日誌
        self.logger.info(f"充值成功: {selected_card.id}, 金額: {amount}, 交易號: {result['tx_no']}")
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"充值失敗: {e}")
        self.logger.error(f"充值失敗: {e}", exc_info=True)
        
        # 友好的錯誤提示
        if "UNSUPPORTED_CARD_TYPE" in str(e):
            print("\n💡 提示：此卡片類型不支持充值")
            print("   只有標準卡可以充值")
        elif "CARD_NOT_FOUND" in str(e):
            print("\n💡 提示：卡片不存在或未激活")
        elif "INVALID_AMOUNT" in str(e):
            print("\n💡 提示：充值金額無效")
            print("   請確保金額在 ¥1 - ¥50,000 之間")
        
        BaseUI.pause()
```

---

#### 1.3 綁定企業卡 - 新功能實現

**參考**: `docs/python_ui_specification.md` 綁定企業卡部分  
**測試**: `tests/test_advanced_business_flow.py` 企業卡綁定測試

**需求**:
```
1. 輸入企業卡 ID
2. 選擇綁定角色（member/viewer）
3. 輸入綁定密碼
4. 顯示綁定結果和企業折扣信息
5. 完整的錯誤處理
```

**實現代碼**:
```python
def _bind_new_card(self):
    """綁定企業卡 - 商業版"""
    try:
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║                綁定企業折扣卡                         ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        print("\n企業折扣卡說明：")
        print("  • 企業卡提供固定折扣，可與多人共享")
        print("  • 綁定後，您的標準卡將繼承企業折扣")
        print("  • 支付時自動選擇最優折扣（積分折扣 vs 企業折扣）")
        print("  • 需要企業卡的綁定密碼才能綁定")
        
        # Step 1: 輸入企業卡 ID
        print("\n" + "─" * 60)
        card_id = input("請輸入企業卡 ID: ").strip()
        
        if not card_id:
            print("❌ 企業卡 ID 不能為空")
            BaseUI.pause()
            return
        
        # 驗證 UUID 格式
        try:
            import uuid
            uuid.UUID(card_id)
        except ValueError:
            print("❌ 企業卡 ID 格式不正確（應為 UUID 格式）")
            BaseUI.pause()
            return
        
        # Step 2: 選擇綁定角色
        print("\n綁定角色：")
        roles = [
            {"code": "member", "name": "成員", "desc": "可以查看卡片信息，使用企業折扣"},
            {"code": "viewer", "name": "查看者", "desc": "只能查看卡片信息，不能使用"}
        ]
        
        for i, role in enumerate(roles, 1):
            print(f"  {i}. {role['name']} - {role['desc']}")
        
        while True:
            try:
                role_choice = int(input(f"\n請選擇角色 (1-{len(roles)}): "))
                if 1 <= role_choice <= len(roles):
                    selected_role = roles[role_choice - 1]
                    break
                print(f"❌ 請輸入 1-{len(roles)}")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        # Step 3: 輸入綁定密碼
        import getpass
        binding_password = getpass.getpass("\n請輸入企業卡綁定密碼: ")
        
        if not binding_password:
            print("❌ 綁定密碼不能為空")
            BaseUI.pause()
            return
        
        # Step 4: 確認綁定
        print("\n" + "═" * 60)
        print("綁定信息確認")
        print("═" * 60)
        print(f"企業卡 ID：  {card_id}")
        print(f"綁定角色：   {selected_role['name']} ({selected_role['desc']})")
        print(f"綁定密碼：   已設置")
        print("═" * 60)
        
        if not BaseUI.confirm("\n確認綁定？"):
            print("❌ 已取消綁定")
            BaseUI.pause()
            return
        
        # Step 5: 執行綁定
        BaseUI.show_loading("正在綁定企業卡...")
        
        result = self.member_service.bind_card(
            card_id,
            self.current_member_id,
            selected_role['code'],
            binding_password
        )
        
        # Step 6: 顯示綁定結果
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║              企業卡綁定成功！                         ║")
        print("╠═══════════════════════════════════════════════════════╣")
        print(f"║  企業卡 ID：{card_id[:20]}...║")
        print(f"║  綁定角色：  {selected_role['name']:<39} ║")
        
        # 如果返回了企業折扣信息
        if result and isinstance(result, dict):
            corporate_discount = result.get('corporate_discount')
            if corporate_discount:
                discount_percent = (1 - float(corporate_discount)) * 100
                print(f"║  企業折扣：  {discount_percent:.1f}% OFF{'':>32} ║")
                print("╠═══════════════════════════════════════════════════════╣")
                print("║  您的標準卡已繼承企業折扣！                          ║")
                print("║  支付時將自動選擇最優折扣                            ║")
        
        print("╚═══════════════════════════════════════════════════════╝")
        
        print("\n✅ 綁定成功！您現在可以享受企業折扣了")
        
        # 記錄日誌
        self.logger.info(f"綁定企業卡成功: {card_id}, 角色: {selected_role['code']}")
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"綁定失敗: {e}")
        self.logger.error(f"綁定企業卡失敗: {e}", exc_info=True)
        
        # 友好的錯誤提示
        if "INVALID_BINDING_PASSWORD" in str(e):
            print("\n💡 提示：綁定密碼錯誤")
            print("   請聯繫企業卡管理員獲取正確的綁定密碼")
        elif "CARD_NOT_FOUND" in str(e):
            print("\n💡 提示：企業卡不存在或未激活")
            print("   請確認企業卡 ID 是否正確")
        elif "CARD_TYPE_NOT_SHAREABLE" in str(e):
            print("\n💡 提示：此卡片類型不支持共享")
            print("   只有企業折扣卡可以綁定")
        elif "ALREADY_BOUND" in str(e):
            print("\n💡 提示：您已經綁定過此企業卡")
        
        BaseUI.pause()
```

---

### Phase 2: 商戶端完善 (Week 2-3)

#### 2.1 退款處理 - 完整實現

**參考**: `docs/python_ui_specification.md` 退款處理部分  
**測試**: `tests/test_complete_business_flow.py` Line 187-249

**需求**:
```
1. 輸入原交易號並查詢
2. 顯示原交易信息和剩餘可退金額
3. 支持部分退款和多次退款
4. 輸入退款原因
5. 顯示退款結果
```

**實現代碼**:
```python
def _process_refund(self):
    """退款處理 - 商業版（支持多次部分退款）"""
    try:
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║                  退款處理                             ║")
        print("║          （支持多次部分退款）                         ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        # Step 1: 輸入原交易號
        tx_no = input("\n請輸入原交易號: ").strip()
        
        if not tx_no:
            print("❌ 交易號不能為空")
            BaseUI.pause()
            return
        
        # Step 2: 查詢原交易
        BaseUI.show_loading("正在查詢交易...")
        
        try:
            # 調用 get_transaction_detail 查詢
            original_tx = self.payment_service.get_transaction_detail(tx_no)
        except Exception as e:
            print(f"\n❌ 查詢交易失敗: {e}")
            print("\n💡 提示：")
            print("   • 請確認交易號是否正確")
            print("   • 只能查詢本商戶的交易")
            BaseUI.pause()
            return
        
        # Step 3: 顯示原交易信息
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║                原交易信息                             ║")
        print("╠═══════════════════════════════════════════════════════╣")
        print(f"║  交易號：    {original_tx.tx_no:<39} ║")
        print(f"║  交易類型：  {original_tx.get_tx_type_display():<39} ║")
        print(f"║  交易金額：  {Formatter.format_currency(original_tx.final_amount):<39} ║")
        print(f"║  交易狀態：  {original_tx.get_status_display():<39} ║")
        print(f"║  交易時間：  {original_tx.format_datetime('created_at'):<39} ║")
        
        # 計算剩餘可退金額
        refunded_amount = self._calculate_total_refunded(tx_no)
        remaining_amount = Decimal(str(original_tx.final_amount)) - refunded_amount
        
        print("╠═══════════════════════════════════════════════════════╣")
        print(f"║  已退金額：  {Formatter.format_currency(refunded_amount):<39} ║")
        print(f"║  剩餘可退：  {Formatter.format_currency(remaining_amount):<39} ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        # 檢查是否可以退款
        if original_tx.status not in ['completed', 'refunded']:
            print("\n❌ 此交易不可退款")
            print(f"   當前狀態：{original_tx.get_status_display()}")
            print("   只有已完成的交易才能退款")
            BaseUI.pause()
            return
        
        if remaining_amount <= 0:
            print("\n❌ 此交易已全額退款，無剩餘可退金額")
            BaseUI.pause()
            return
        
        # Step 4: 輸入退款金額
        print(f"\n可退款金額：{Formatter.format_currency(remaining_amount)}")
        
        while True:
            try:
                refund_amount_str = input(f"請輸入退款金額 (0.01-{remaining_amount}): ").strip()
                refund_amount = Decimal(refund_amount_str)
                
                if refund_amount <= 0:
                    print("❌ 退款金額必須大於 0")
                    continue
                if refund_amount > remaining_amount:
                    print(f"❌ 退款金額不能超過剩餘可退金額 {Formatter.format_currency(remaining_amount)}")
                    continue
                
                break
            except (ValueError, InvalidOperation):
                print("❌ 請輸入有效的金額")
        
        # Step 5: 輸入退款原因
        print("\n退款原因（可選）：")
        reason = input("請輸入退款原因: ").strip()
        if not reason:
            reason = "客戶要求退款"
        
        # Step 6: 確認退款
        print("\n" + "═" * 60)
        print("退款信息確認")
        print("═" * 60)
        print(f"原交易號：    {tx_no}")
        print(f"原交易金額：  {Formatter.format_currency(original_tx.final_amount)}")
        print(f"已退金額：    {Formatter.format_currency(refunded_amount)}")
        print(f"本次退款：    {Formatter.format_currency(refund_amount)}")
        print(f"退款後剩餘：  {Formatter.format_currency(remaining_amount - refund_amount)}")
        print(f"退款原因：    {reason}")
        print("═" * 60)
        
        if not BaseUI.confirm("\n確認退款？"):
            print("❌ 已取消退款")
            BaseUI.pause()
            return
        
        # Step 7: 執行退款
        BaseUI.show_loading("正在處理退款...")
        
        refund_result = self.payment_service.refund_transaction(
            self.current_merchant_code,
            tx_no,
            refund_amount,
            reason
        )
        
        # Step 8: 顯示退款結果
        BaseUI.clear_screen()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║                退款成功！                             ║")
        print("╠═══════════════════════════════════════════════════════╣")
        print(f"║  退款交易號：{refund_result['refund_tx_no']:<39} ║")
        print(f"║  原交易號：  {tx_no:<39} ║")
        print(f"║  退款金額：  {Formatter.format_currency(refund_amount):<39} ║")
        print(f"║  退款原因：  {reason[:35]:<39} ║")
        print(f"║  處理時間：  {Formatter.format_datetime(refund_result.get('created_at')):<39} ║")
        print("╚═══════════════════════════════════════════════════════╝")
        
        print("\n✅ 退款已處理，金額將退回客戶卡片")
        
        # 記錄日誌
        self.logger.info(f"退款成功: {tx_no}, 金額: {refund_amount}, 退款單號: {refund_result['refund_tx_no']}")
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"退款失敗: {e}")
        self.logger.error(f"退款失敗: {e}", exc_info=True)
        
        # 友好的錯誤提示
        if "REFUND_EXCEEDS_REMAINING" in str(e):
            print("\n💡 提示：退款金額超過剩餘可退金額")
            print("   此交易可能已經部分退款")
        elif "ONLY_COMPLETED_PAYMENT_REFUNDABLE" in str(e):
            print("\n💡 提示：只能退款已完成的支付交易")
        elif "NOT_AUTHORIZED" in str(e):
            print("\n💡 提示：沒有權限操作此交易")
            print("   只能退款本商戶的交易")
        
        BaseUI.pause()

def _calculate_total_refunded(self, original_tx_no: str) -> Decimal:
    """計算已退款總金額"""
    try:
        # 查詢所有退款記錄
        refunds = self.payment_service.get_refund_history(original_tx_no)
        total = Decimal("0")
        for refund in refunds:
            if refund.get('status') == 'completed':
                total += Decimal(str(refund.get('amount', 0)))
        return total
    except:
        return Decimal("0")
```

---

## 📊 實施進度追蹤

| 功能模塊 | 優先級 | 預計工時 | 狀態 | 負責人 |
|---------|--------|---------|------|--------|
| 會員-生成QR | P0 | 4h | 待開始 | - |
| 會員-充值 | P0 | 4h | 待開始 | - |
| 會員-綁定企業卡 | P1 | 3h | 待開始 | - |
| 會員-查看積分 | P1 | 2h | 待開始 | - |
| 商戶-退款處理 | P0 | 4h | 待開始 | - |
| 商戶-今日統計 | P1 | 3h | 待開始 | - |
| 商戶-結算報表 | P1 | 4h | 待開始 | - |
| 管理-會員管理 | P1 | 6h | 待開始 | - |
| 管理-商戶管理 | P1 | 6h | 待開始 | - |
| 管理-卡片管理 | P1 | 4h | 待開始 | - |

**總預計工時**: 40 小時  
**目標完成時間**: 2 週

---

## ✅ 質量標準

### 代碼質量
- [ ] 所有函數都有完整的文檔字符串
- [ ] 所有錯誤都有友好的提示信息
- [ ] 所有用戶輸入都有驗證
- [ ] 所有操作都有確認步驟

### 用戶體驗
- [ ] 界面清晰美觀，使用 Unicode 字符繪製
- [ ] 操作流程順暢，步驟明確
- [ ] 錯誤提示友好，提供解決方案
- [ ] 重要信息突出顯示

### 測試覆蓋
- [ ] 每個功能都有對應的測試用例
- [ ] 測試覆蓋正常流程和異常流程
- [ ] 所有測試都能通過

---

**最後更新**: 2025-10-01  
**文檔版本**: v1.0.0  
**下一步**: 開始實施 Phase 1
