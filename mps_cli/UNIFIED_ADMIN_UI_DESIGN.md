# MPS Admin UI 統一設計方案

> 設計時間：2025-10-06  
> 核心原則：**零 UUID 暴露 + 智能搜尋 + 直接操作**  
> 目標：最直覺、最高效的 Admin 操作體驗

---

## 🎯 核心設計原則

### 1. 零 UUID 暴露原則 ⭐⭐⭐⭐⭐

**絕對不在界面上顯示或要求輸入 UUID**

```
✅ 允許的識別碼：
- 會員號：M202501001
- 手機號：13800138000
- 郵箱：user@example.com
- 卡號：C202501001
- 商戶代碼：SHOP001

❌ 禁止的識別碼：
- UUID：550e8400-e29b-41d4-a716-446655440000
```

### 2. 智能搜尋原則 ⭐⭐⭐⭐⭐

**支持模糊搜尋，自動匹配多個結果**

```
輸入：138
結果：
  1. M202501001 - 張三 - 13800138000
  2. M202501002 - 李四 - 13812345678
  3. M202501003 - 王五 - 13898765432
```

### 3. 序號選擇原則 ⭐⭐⭐⭐⭐

**從搜尋結果中選擇序號，而不是輸入識別碼**

```
請選擇 (1-3): 1
→ 進入張三的操作菜單
```

---

## 🎨 統一的操作流程

### 標準流程

```
1. 輸入搜尋關鍵字
   ↓
2. 顯示匹配結果（可能多個）
   ↓
3. 選擇序號
   ↓
4. 進入實體操作菜單
   ↓
5. 執行操作 / 返回搜尋
```

---

## 💡 會員管理設計

### 新的會員管理菜單

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          會員管理                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝

1. 🔍 搜尋並管理會員 (Search & Manage Members)
2. 📋 瀏覽所有會員 (Browse All Members)
3. ➕ 創建新會員 (Create New Member)
4. 🔙 返回主菜單 (Return to Main Menu)
```

### 功能 1：搜尋並管理會員（主要功能）

#### 流程設計

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                      搜尋並管理會員                                       ║
╚═══════════════════════════════════════════════════════════════════════════╝

💡 您可以輸入：
  • 會員號（如：M202501001）
  • 姓名（如：張三）
  • 手機號（如：138）- 支持部分匹配
  • 郵箱（如：user@example.com）

請輸入搜尋關鍵字: 138

🔍 搜尋結果（找到 3 個會員）：
─────────────────────────────────────────────────────────────────────────
序號  會員號        姓名      手機           郵箱                    狀態
─────────────────────────────────────────────────────────────────────────
1     M202501001    張三      13800138000    zhang@example.com      活躍
2     M202501002    李四      13812345678    li@example.com         活躍
3     M202501003    王五      13898765432    wang@example.com       暫停
─────────────────────────────────────────────────────────────────────────

操作選項：
  [1-3] 選擇會員進行操作
  [R] 重新搜尋
  [Q] 返回

請選擇: 1

→ 進入「張三」的操作菜單
```

#### 實現代碼

```python
def _search_and_manage_members(self):
    """搜尋並管理會員 - 統一入口"""
    while True:
        BaseUI.clear_screen()
        BaseUI.show_header("搜尋並管理會員")
        
        # 1. 顯示搜尋提示
        print("\n💡 您可以輸入：")
        print("  • 會員號（如：M202501001）")
        print("  • 姓名（如：張三）")
        print("  • 手機號（如：138）- 支持部分匹配")
        print("  • 郵箱（如：user@example.com）")
        
        keyword = input("\n請輸入搜尋關鍵字（或按 Enter 返回）: ").strip()
        
        if not keyword:
            return
        
        # 2. 執行搜尋
        BaseUI.show_loading("搜尋中...")
        
        try:
            members = self.member_service.search_members(keyword, 50)
            
            if not members:
                BaseUI.show_info("未找到匹配的會員")
                BaseUI.pause()
                continue
            
            # 3. 顯示搜尋結果
            selected_member = self._display_and_select_member(members, keyword)
            
            if selected_member:
                # 4. 進入會員操作菜單
                self._member_action_menu(selected_member)
            
        except Exception as e:
            BaseUI.show_error(f"搜尋失敗：{e}")
            BaseUI.pause()

def _display_and_select_member(self, members: List[Member], keyword: str) -> Optional[Member]:
    """顯示搜尋結果並選擇會員"""
    while True:
        BaseUI.clear_screen()
        
        # 顯示搜尋結果
        print(f"🔍 搜尋結果（關鍵字：{keyword}，找到 {len(members)} 個會員）：")
        print("─" * 79)
        print(f"{'序號':<4} {'會員號':<12} {'姓名':<10} {'手機':<13} "
              f"{'郵箱':<20} {'狀態':<8}")
        print("─" * 79)
        
        for i, member in enumerate(members, 1):
            print(f"{i:<4} {member.member_no:<12} {member.name:<10} "
                  f"{member.phone:<13} {member.email:<20} "
                  f"{member.get_status_display():<8}")
        
        print("─" * 79)
        
        # 操作選項
        print("\n操作選項：")
        print(f"  [1-{len(members)}] 選擇會員進行操作")
        print("  [R] 重新搜尋")
        print("  [Q] 返回")
        
        choice = input("\n請選擇: ").strip().upper()
        
        if choice == 'R':
            return None  # 重新搜尋
        elif choice == 'Q':
            return None  # 返回
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(members):
                return members[idx - 1]
            else:
                BaseUI.show_error(f"請輸入 1-{len(members)}")
                BaseUI.pause()
        else:
            BaseUI.show_error("無效的選擇")
            BaseUI.pause()

def _member_action_menu(self, member: Member):
    """會員操作菜單 - 零 UUID 暴露"""
    while True:
        BaseUI.clear_screen()
        
        # 顯示會員信息（不包含 UUID）
        print("═" * 79)
        print(f"會員操作 - {member.name}")
        print("═" * 79)
        print(f"會員號：  {member.member_no}")
        print(f"姓名：    {member.name}")
        print(f"手機：    {member.phone}")
        print(f"郵箱：    {member.email}")
        print(f"狀態：    {member.get_status_display()}")
        print(f"創建時間：{member.format_datetime('created_at')}")
        print("═" * 79)
        
        # 操作選項
        options = [
            "📋 查看完整詳情 (View Full Details)",
            "✏️  編輯資料 (Edit Profile)",
            "🔒 重置密碼 (Reset Password)",
            "💳 管理卡片 (Manage Cards)",
            "📊 查看交易記錄 (View Transactions)",
            "⏸️  暫停/激活 (Suspend/Activate)",
            "🔙 返回搜尋 (Back to Search)"
        ]
        
        choice = BaseUI.show_menu(options, "請選擇操作")
        
        if choice == 1:
            self._view_member_full_details(member)
        elif choice == 2:
            self._edit_member_profile(member)
        elif choice == 3:
            self._reset_member_password_direct(member)
        elif choice == 4:
            self._manage_member_cards(member)
        elif choice == 5:
            self._view_member_transactions(member)
        elif choice == 6:
            self._toggle_member_status(member)
        elif choice == 7:
            break

def _edit_member_profile(self, member: Member):
    """編輯會員資料 - 直接操作，無需輸入識別碼"""
    try:
        BaseUI.clear_screen()
        BaseUI.show_header(f"編輯會員資料 - {member.name}")
        
        # 顯示當前信息
        print("\n當前信息：")
        print(f"  姓名：{member.name}")
        print(f"  手機：{member.phone}")
        print(f"  郵箱：{member.email}")
        
        # 輸入新信息
        print("\n請輸入新信息（留空保持不變）：")
        new_name = input(f"姓名 [{member.name}]: ").strip() or None
        new_phone = input(f"手機 [{member.phone}]: ").strip() or None
        new_email = input(f"郵箱 [{member.email}]: ").strip() or None
        
        if not any([new_name, new_phone, new_email]):
            BaseUI.show_info("沒有需要更新的內容")
            BaseUI.pause()
            return
        
        # 顯示更新摘要
        print("\n更新摘要：")
        if new_name:
            print(f"  姓名：{member.name} → {new_name}")
        if new_phone:
            print(f"  手機：{member.phone} → {new_phone}")
        if new_email:
            print(f"  郵箱：{member.email} → {new_email}")
        
        if not BaseUI.confirm("\n確認更新？"):
            BaseUI.show_info("已取消")
            BaseUI.pause()
            return
        
        # 執行更新（使用會員號，內部轉換為 UUID）
        BaseUI.show_loading("更新中...")
        result = self.member_service.update_member_profile(
            member.member_no,  # 使用會員號
            new_name,
            new_phone,
            new_email
        )
        
        if result:
            # 更新本地對象
            if new_name:
                member.name = new_name
            if new_phone:
                member.phone = new_phone
            if new_email:
                member.email = new_email
            
            BaseUI.show_success("會員資料更新成功")
        else:
            BaseUI.show_error("會員資料更新失敗")
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"更新失敗：{e}")
        BaseUI.pause()

def _reset_member_password_direct(self, member: Member):
    """重置會員密碼 - 直接操作，無需輸入識別碼"""
    try:
        BaseUI.clear_screen()
        BaseUI.show_header(f"重置密碼 - {member.name}")
        
        # 顯示會員信息
        print("\n會員信息：")
        print(f"  會員號：{member.member_no}")
        print(f"  姓名：  {member.name}")
        print(f"  手機：  {member.phone}")
        
        # 密碼重置選項
        print("\n🔒 密碼重置選項：")
        print("1. 重置為手機號")
        print("2. 設置自定義密碼")
        print("3. 取消")
        
        choice = input("\n請選擇 (1-3): ").strip()
        
        new_password = None
        password_display = ""
        
        if choice == "1":
            new_password = member.phone
            password_display = f"手機號：{member.phone}"
        elif choice == "2":
            import getpass
            while True:
                new_password = getpass.getpass("\n請輸入新密碼: ")
                if not new_password:
                    BaseUI.show_error("密碼不能為空")
                    continue
                
                if len(new_password) < 6:
                    BaseUI.show_error("密碼長度至少 6 個字符")
                    continue
                
                confirm = getpass.getpass("請確認新密碼: ")
                if new_password != confirm:
                    BaseUI.show_error("兩次密碼輸入不一致")
                    continue
                
                password_display = "自定義密碼"
                break
        elif choice == "3":
            BaseUI.show_info("已取消")
            BaseUI.pause()
            return
        else:
            BaseUI.show_error("無效的選擇")
            BaseUI.pause()
            return
        
        # 確認重置
        print("\n" + "═" * 79)
        print(f"確認重置 {member.name} 的密碼")
        print(f"新密碼：{password_display}")
        print("═" * 79)
        
        if not BaseUI.confirm("\n確認重置？"):
            BaseUI.show_info("已取消")
            BaseUI.pause()
            return
        
        # 執行重置（使用會員號）
        BaseUI.show_loading("重置中...")
        self.member_service.set_member_password(member.member_no, new_password)
        
        BaseUI.show_success("密碼重置成功", {
            "會員": member.name,
            "新密碼": password_display
        })
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"重置失敗：{e}")
        BaseUI.pause()
```

---

### 功能 2：瀏覽所有會員

#### 流程設計

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                      瀏覽所有會員 - 第 1 頁                               ║
╚═══════════════════════════════════════════════════════════════════════════╝

─────────────────────────────────────────────────────────────────────────
序號  會員號        姓名      手機           郵箱                    狀態
─────────────────────────────────────────────────────────────────────────
1     M202501001    張三      13800138000    zhang@example.com      活躍
2     M202501002    李四      13812345678    li@example.com         活躍
3     M202501003    王五      13898765432    wang@example.com       暫停
...
20    M202501020    趙六      13999999999    zhao@example.com       活躍
─────────────────────────────────────────────────────────────────────────

📄 第 1 / 5 頁 | 共 100 個會員

操作選項：
  [1-20] 選擇會員進行操作
  [N] 下一頁
  [P] 上一頁
  [S] 搜尋
  [Q] 返回

請選擇: 
```

#### 實現代碼

```python
def _browse_all_members(self):
    """瀏覽所有會員 - 改進版"""
    page = 1
    page_size = 20
    
    while True:
        try:
            BaseUI.clear_screen()
            BaseUI.show_header(f"瀏覽所有會員 - 第 {page} 頁")
            
            BaseUI.show_loading("載入中...")
            
            # 獲取會員列表
            offset = (page - 1) * page_size
            result = self.member_service.get_all_members(page_size, offset)
            
            members = result['data']
            pagination = result['pagination']
            
            if not members:
                BaseUI.show_info("沒有會員記錄")
                BaseUI.pause()
                return
            
            # 顯示會員列表（不包含 UUID）
            print("\n─" * 79)
            print(f"{'序號':<4} {'會員號':<12} {'姓名':<10} {'手機':<13} "
                  f"{'郵箱':<20} {'狀態':<8}")
            print("─" * 79)
            
            for i, member in enumerate(members, 1):
                print(f"{i:<4} {member.member_no:<12} {member.name:<10} "
                      f"{member.phone:<13} {member.email:<20} "
                      f"{member.get_status_display():<8}")
            
            print("─" * 79)
            
            # 分頁信息
            print(f"\n📄 第 {page} / {pagination['total_pages']} 頁 | "
                  f"共 {pagination['total_count']} 個會員")
            
            # 操作選項
            print("\n操作選項：")
            print(f"  [1-{len(members)}] 選擇會員進行操作")
            if pagination['has_next']:
                print("  [N] 下一頁")
            if pagination['has_prev']:
                print("  [P] 上一頁")
            print("  [S] 搜尋")
            print("  [Q] 返回")
            
            choice = input("\n請選擇: ").strip().upper()
            
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(members):
                    selected_member = members[idx - 1]
                    self._member_action_menu(selected_member)
                else:
                    BaseUI.show_error(f"請輸入 1-{len(members)}")
                    BaseUI.pause()
            elif choice == 'N' and pagination['has_next']:
                page += 1
            elif choice == 'P' and pagination['has_prev']:
                page -= 1
            elif choice == 'S':
                self._search_and_manage_members()
            elif choice == 'Q':
                break
            else:
                BaseUI.show_error("無效的選擇")
                BaseUI.pause()
                
        except Exception as e:
            BaseUI.show_error(f"瀏覽失敗：{e}")
            BaseUI.pause()
            break
```

---

## 💳 卡片管理設計

### 新的卡片管理菜單

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          卡片管理                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝

1. 🔍 搜尋並管理卡片 (Search & Manage Cards)
2. 📋 瀏覽所有卡片 (Browse All Cards)
3. ➕ 創建企業卡 (Create Corporate Card)
4. 🔙 返回主菜單 (Return to Main Menu)
```

### 搜尋並管理卡片

```python
def _search_and_manage_cards(self):
    """搜尋並管理卡片"""
    while True:
        BaseUI.clear_screen()
        BaseUI.show_header("搜尋並管理卡片")
        
        print("\n💡 您可以輸入：")
        print("  • 卡號（如：C202501001）")
        print("  • 持卡人姓名（如：張三）")
        print("  • 持卡人手機（如：138）")
        
        keyword = input("\n請輸入搜尋關鍵字（或按 Enter 返回）: ").strip()
        
        if not keyword:
            return
        
        BaseUI.show_loading("搜尋中...")
        
        try:
            cards = self.admin_service.search_cards_advanced(keyword, 50)
            
            if not cards:
                BaseUI.show_info("未找到匹配的卡片")
                BaseUI.pause()
                continue
            
            selected_card = self._display_and_select_card(cards, keyword)
            
            if selected_card:
                self._card_action_menu(selected_card)
                
        except Exception as e:
            BaseUI.show_error(f"搜尋失敗：{e}")
            BaseUI.pause()

def _display_and_select_card(self, cards: List[Card], keyword: str) -> Optional[Card]:
    """顯示搜尋結果並選擇卡片"""
    while True:
        BaseUI.clear_screen()
        
        print(f"🔍 搜尋結果（關鍵字：{keyword}，找到 {len(cards)} 張卡片）：")
        print("─" * 79)
        print(f"{'序號':<4} {'卡號':<12} {'類型':<10} {'持卡人':<10} "
              f"{'餘額':<12} {'狀態':<8}")
        print("─" * 79)
        
        for i, card in enumerate(cards, 1):
            print(f"{i:<4} {card.card_no:<12} {card.get_card_type_display():<10} "
                  f"{card.owner_name or 'N/A':<10} "
                  f"{Formatter.format_currency(card.balance):<12} "
                  f"{card.get_status_display():<8}")
        
        print("─" * 79)
        
        print("\n操作選項：")
        print(f"  [1-{len(cards)}] 選擇卡片進行操作")
        print("  [R] 重新搜尋")
        print("  [Q] 返回")
        
        choice = input("\n請選擇: ").strip().upper()
        
        if choice == 'R':
            return None
        elif choice == 'Q':
            return None
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(cards):
                return cards[idx - 1]
            else:
                BaseUI.show_error(f"請輸入 1-{len(cards)}")
                BaseUI.pause()
        else:
            BaseUI.show_error("無效的選擇")
            BaseUI.pause()

def _card_action_menu(self, card: Card):
    """卡片操作菜單 - 零 UUID 暴露"""
    while True:
        BaseUI.clear_screen()
        
        # 顯示卡片信息（不包含 UUID）
        print("═" * 79)
        print(f"卡片操作 - {card.card_no}")
        print("═" * 79)
        print(f"卡號：    {card.card_no}")
        print(f"類型：    {card.get_card_type_display()}")
        print(f"持卡人：  {card.owner_name or 'N/A'}")
        print(f"餘額：    {Formatter.format_currency(card.balance)}")
        print(f"積分：    {card.points or 0}")
        print(f"等級：    {card.get_level_display()}")
        print(f"狀態：    {card.get_status_display()}")
        print("═" * 79)
        
        options = [
            "📋 查看完整詳情 (View Full Details)",
            "👤 查看持卡人信息 (View Owner Info)",
            "📊 查看交易記錄 (View Transactions)",
            "❄️  凍結/解凍 (Freeze/Unfreeze)",
            "💰 調整餘額 (Adjust Balance)",
            "🔙 返回搜尋 (Back to Search)"
        ]
        
        choice = BaseUI.show_menu(options, "請選擇操作")
        
        if choice == 1:
            self._view_card_full_details(card)
        elif choice == 2:
            self._view_card_owner_info(card)
        elif choice == 3:
            self._view_card_transactions(card)
        elif choice == 4:
            self._toggle_card_status(card)
        elif choice == 5:
            self._adjust_card_balance(card)
        elif choice == 6:
            break
```

---

## 🏪 商戶管理設計

### 搜尋並管理商戶

```python
def _search_and_manage_merchants(self):
    """搜尋並管理商戶"""
    while True:
        BaseUI.clear_screen()
        BaseUI.show_header("搜尋並管理商戶")
        
        print("\n💡 您可以輸入：")
        print("  • 商戶代碼（如：SHOP001）")
        print("  • 商戶名稱（如：測試商店）")
        
        keyword = input("\n請輸入搜尋關鍵字（或按 Enter 返回）: ").strip()
        
        if not keyword:
            return
        
        BaseUI.show_loading("搜尋中...")
        
        try:
            merchants = self.admin_service.search_merchants(keyword, 50)
            
            if not merchants:
                BaseUI.show_info("未找到匹配的商戶")
                BaseUI.pause()
                continue
            
            selected_merchant = self._display_and_select_merchant(merchants, keyword)
            
            if selected_merchant:
                self._merchant_action_menu(selected_merchant)
                
        except Exception as e:
            BaseUI.show_error(f"搜尋失敗：{e}")
            BaseUI.pause()

def _merchant_action_menu(self, merchant):
    """商戶操作菜單 - 零 UUID 暴露"""
    while True:
        BaseUI.clear_screen()
        
        # 顯示商戶信息（不包含 UUID）
        print("═" * 79)
        print(f"商戶操作 - {merchant.name}")
        print("═" * 79)
        print(f"商戶代碼：{merchant.code}")
        print(f"商戶名稱：{merchant.name}")
        print(f"聯繫人：  {merchant.contact}")
        print(f"狀態：    {merchant.get_status_display()}")
        print("═" * 79)
        
        options = [
            "📋 查看完整詳情 (View Full Details)",
            "✏️  編輯資料 (Edit Profile)",
            "🔒 重置密碼 (Reset Password)",
            "📊 查看交易記錄 (View Transactions)",
            "💰 查看結算記錄 (View Settlements)",
            "⏸️  暫停/激活 (Suspend/Activate)",
            "🔙 返回搜尋 (Back to Search)"
        ]
        
        choice = BaseUI.show_menu(options, "請選擇操作")
        
        if choice == 1:
            self._view_merchant_full_details(merchant)
        elif choice == 2:
            self._edit_merchant_profile(merchant)
        elif choice == 3:
            self._reset_merchant_password_direct(merchant)
        elif choice == 4:
            self._view_merchant_transactions(merchant)
        elif choice == 5:
            self._view_merchant_settlements(merchant)
        elif choice == 6:
            self._toggle_merchant_status(merchant)
        elif choice == 7:
            break
```

---

## 📊 實施優先級

### P0 - 立即實施（必須）⭐⭐⭐⭐⭐

1. **會員搜尋並管理** - 3 天
   - 智能搜尋功能
   - 序號選擇機制
   - 會員操作菜單
   - 零 UUID 暴露

2. **卡片搜尋並管理** - 2 天
   - 卡片搜尋功能
   - 卡片操作菜單

3. **商戶搜尋並管理** - 2 天
   - 商戶搜尋功能
   - 商戶操作菜單

**總計：7 天**

---

## ✅ 驗收標準

### 功能完整性
- [ ] 所有實體支持智能搜尋
- [ ] 搜尋支持部分匹配
- [ ] 可以從搜尋結果選擇序號
- [ ] 所有操作菜單完整

### 零 UUID 暴露
- [ ] **界面上完全看不到 UUID**
- [ ] 所有輸入使用業務識別碼
- [ ] 所有顯示使用業務識別碼
- [ ] 內部自動轉換 UUID

### 用戶體驗
- [ ] 搜尋速度 < 2 秒
- [ ] 操作流程直覺
- [ ] 提示信息清晰
- [ ] 錯誤處理友好

---

## 📝 總結

### 核心特點

1. **零 UUID 暴露** ✅
   - 界面上完全看不到 UUID
   - 使用會員號、卡號、商戶代碼

2. **智能搜尋** ✅
   - 支持部分匹配
   - 自動顯示多個結果
   - 輸入序號選擇

3. **直接操作** ✅
   - 選擇後直接進入操作菜單
   - 無需重新輸入識別碼
   - 操作流程連貫

4. **統一體驗** ✅
   - 所有實體使用相同流程
   - 一致的操作邏輯
   - 標準化的界面設計

---

**設計人員**: AI Assistant  
**設計日期**: 2025-10-06  
**實施優先級**: P0 - 最高優先級  
**預估工時**: 7 天
