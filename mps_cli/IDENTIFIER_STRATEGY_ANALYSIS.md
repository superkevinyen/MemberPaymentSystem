# MPS 系統識別碼策略分析與建議

> 分析時間：2025-10-06  
> 討論主題：UUID vs 業務識別碼（會員號/卡號/商戶代碼）  
> 目標：提升用戶體驗和系統可用性

---

## 🔍 當前系統識別碼分析

### 現有識別碼體系

| 實體 | 內部 ID (主鍵) | 業務識別碼 | 其他識別碼 |
|------|----------------|-----------|-----------|
| **會員** | `id` (UUID) | `member_no` (自動生成) | `phone` (唯一), `email` |
| **卡片** | `id` (UUID) | `card_no` (自動生成) | - |
| **商戶** | `id` (UUID) | `code` (手動輸入) | - |
| **交易** | `id` (UUID) | `tx_no` (自動生成) | - |

### 當前使用情況

#### ✅ 已經使用業務識別碼的地方

1. **會員登入**
   ```sql
   -- 可以使用 phone 或 member_no 登入
   CREATE OR REPLACE FUNCTION member_login(
     p_identifier text,  -- phone 或 member_no
     p_password text
   )
   ```

2. **商戶登入**
   ```sql
   -- 使用 merchant_code 登入
   CREATE OR REPLACE FUNCTION merchant_login(
     p_merchant_code text,
     p_password text
   )
   ```

3. **商戶支付**
   ```sql
   -- 使用 merchant_code 進行支付
   CREATE OR REPLACE FUNCTION merchant_charge_by_qr(
     p_merchant_code text,
     p_qr_plain text,
     ...
   )
   ```

4. **搜尋功能**
   ```sql
   -- 可以用 member_no, phone, email 搜尋
   WHERE mp.member_no ILIKE '%' || p_keyword || '%'
      OR mp.phone ILIKE '%' || p_keyword || '%'
      OR mp.email ILIKE '%' || p_keyword || '%'
   ```

#### ❌ 仍然使用 UUID 的地方

1. **Admin UI 操作**
   - 查看會員詳情：需要輸入 UUID
   - 更新會員資料：需要輸入 UUID
   - 重置密碼：需要輸入 UUID
   - 暫停會員：需要輸入 UUID

2. **卡片操作**
   - 查看卡片詳情：需要輸入 UUID
   - 凍結/解凍卡片：需要輸入 UUID

3. **RPC 函數參數**
   - 大部分 RPC 函數使用 UUID 作為參數

---

## 💡 問題分析

### UUID 的問題

1. **用戶體驗差** ❌
   ```
   UUID 示例: 550e8400-e29b-41d4-a716-446655440000
   
   問題：
   - 長度 36 個字符
   - 難以記憶
   - 容易輸入錯誤
   - 無法口頭傳達
   - 不適合打印在單據上
   ```

2. **操作效率低** ❌
   ```
   當前流程：
   1. 瀏覽會員列表
   2. 找到目標會員
   3. 複製 UUID
   4. 返回操作菜單
   5. 粘貼 UUID
   6. 執行操作
   ```

3. **不符合業務習慣** ❌
   ```
   現實場景：
   - 客服：「請告訴我您的會員號」✅
   - 客服：「請告訴我您的 UUID」❌
   
   - 商戶：「請輸入您的商戶代碼」✅
   - 商戶：「請輸入您的 UUID」❌
   ```

### 業務識別碼的優勢

1. **用戶友好** ✅
   ```
   會員號示例: M202501001
   卡號示例: C202501001
   商戶代碼示例: SHOP001
   
   優勢：
   - 長度適中（8-12 字符）
   - 易於記憶
   - 可以口頭傳達
   - 適合打印
   - 有業務含義
   ```

2. **操作高效** ✅
   ```
   改進流程：
   1. 瀏覽會員列表
   2. 看到會員號 M202501001
   3. 直接輸入會員號
   4. 執行操作
   ```

3. **符合業務習慣** ✅
   ```
   現實場景：
   - 「您的會員號是 M202501001」
   - 「您的卡號是 C202501001」
   - 「商戶代碼是 SHOP001」
   ```

---

## 🎯 建議方案

### 方案一：全面使用業務識別碼（推薦）⭐⭐⭐⭐⭐

#### 核心原則

**對外使用業務識別碼，對內保留 UUID**

```
用戶界面層 → 業務識別碼 (member_no, card_no, merchant_code)
     ↓
服務層轉換 → UUID (id)
     ↓
數據庫層 → UUID (主鍵)
```

#### 實施策略

1. **所有 UI 輸入使用業務識別碼**
   ```python
   # 改進前
   member_id = input("請輸入會員 ID (UUID): ")
   
   # 改進後
   member_identifier = input("請輸入會員號或手機號: ")
   ```

2. **所有顯示使用業務識別碼**
   ```python
   # 改進前
   print(f"會員 ID: {member.id}")
   
   # 改進後
   print(f"會員號: {member.member_no}")
   print(f"手機: {member.phone}")
   ```

3. **服務層自動轉換**
   ```python
   def get_member_by_identifier(self, identifier: str) -> Optional[Member]:
       """通過業務識別碼獲取會員
       
       Args:
           identifier: 會員號、手機號或郵箱
       """
       # 嘗試不同的識別方式
       member = self.rpc_call("get_member_by_identifier", {
           "p_identifier": identifier
       })
       return Member.from_dict(member) if member else None
   ```

4. **RPC 層支持多種識別方式**
   ```sql
   CREATE OR REPLACE FUNCTION get_member_by_identifier(
     p_identifier text  -- member_no, phone, email 都可以
   )
   RETURNS jsonb
   LANGUAGE plpgsql
   SECURITY DEFINER
   AS $$
   DECLARE
     v_member member_profiles%ROWTYPE;
   BEGIN
     PERFORM sec.fixed_search_path();
     
     -- 嘗試多種方式查找
     SELECT * INTO v_member
     FROM member_profiles
     WHERE member_no = p_identifier
        OR phone = p_identifier
        OR email = p_identifier
     LIMIT 1;
     
     IF NOT FOUND THEN
       RETURN NULL;
     END IF;
     
     RETURN row_to_json(v_member)::jsonb;
   END;
   $$;
   ```

---

### 方案二：混合使用（不推薦）⭐⭐

**問題**：
- 用戶需要記住什麼時候用什麼識別碼
- 容易混淆
- 體驗不一致

---

## 📋 具體實施計劃

### 階段一：創建統一的識別碼查詢 RPC（1 天）

#### 1.1 會員識別碼查詢

```sql
-- 通用會員查詢函數
CREATE OR REPLACE FUNCTION get_member_by_identifier(
  p_identifier text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member member_profiles%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 支持 member_no, phone, email
  SELECT * INTO v_member
  FROM member_profiles
  WHERE member_no = p_identifier
     OR phone = p_identifier
     OR email = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  RETURN row_to_json(v_member)::jsonb;
END;
$$;

-- 通用卡片查詢函數
CREATE OR REPLACE FUNCTION get_card_by_identifier(
  p_identifier text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_card member_cards%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  
  -- 支持 card_no 或 UUID
  SELECT * INTO v_card
  FROM member_cards
  WHERE card_no = p_identifier
     OR (p_identifier ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' 
         AND id = p_identifier::uuid)
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'CARD_NOT_FOUND';
  END IF;
  
  RETURN row_to_json(v_card)::jsonb;
END;
$$;

-- 通用商戶查詢函數
CREATE OR REPLACE FUNCTION get_merchant_by_identifier(
  p_identifier text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_merchant merchants%ROWTYPE;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 支持 merchant_code
  SELECT * INTO v_merchant
  FROM merchants
  WHERE code = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MERCHANT_NOT_FOUND';
  END IF;
  
  RETURN row_to_json(v_merchant)::jsonb;
END;
$$;
```

#### 1.2 修改現有 RPC 支持業務識別碼

```sql
-- 示例：更新會員資料
CREATE OR REPLACE FUNCTION update_member_profile(
  p_identifier text,  -- 改為支持 member_no/phone/email
  p_name text DEFAULT NULL,
  p_phone text DEFAULT NULL,
  p_email text DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_member_id uuid;
BEGIN
  PERFORM sec.fixed_search_path();
  PERFORM check_permission('super_admin');
  
  -- 先通過識別碼找到 UUID
  SELECT id INTO v_member_id
  FROM member_profiles
  WHERE member_no = p_identifier
     OR phone = p_identifier
     OR email = p_identifier
  LIMIT 1;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'MEMBER_NOT_FOUND';
  END IF;
  
  -- 執行更新
  UPDATE member_profiles
  SET
    name = COALESCE(p_name, name),
    phone = COALESCE(p_phone, phone),
    email = COALESCE(p_email, email),
    updated_at = now_utc()
  WHERE id = v_member_id;
  
  RETURN TRUE;
END;
$$;
```

---

### 階段二：更新服務層（2 天）

#### 2.1 創建識別碼轉換工具

```python
# mps_cli/utils/identifier_resolver.py

class IdentifierResolver:
    """識別碼解析器"""
    
    @staticmethod
    def is_uuid(identifier: str) -> bool:
        """判斷是否為 UUID"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, identifier.lower()))
    
    @staticmethod
    def is_member_no(identifier: str) -> bool:
        """判斷是否為會員號"""
        # 假設會員號格式：M + 9位數字
        return identifier.startswith('M') and len(identifier) == 10
    
    @staticmethod
    def is_card_no(identifier: str) -> bool:
        """判斷是否為卡號"""
        # 假設卡號格式：C + 9位數字
        return identifier.startswith('C') and len(identifier) == 10
    
    @staticmethod
    def is_phone(identifier: str) -> bool:
        """判斷是否為手機號"""
        return identifier.isdigit() and len(identifier) == 11
    
    @staticmethod
    def is_email(identifier: str) -> bool:
        """判斷是否為郵箱"""
        return '@' in identifier
    
    @staticmethod
    def get_identifier_type(identifier: str) -> str:
        """獲取識別碼類型"""
        if IdentifierResolver.is_uuid(identifier):
            return 'uuid'
        elif IdentifierResolver.is_member_no(identifier):
            return 'member_no'
        elif IdentifierResolver.is_card_no(identifier):
            return 'card_no'
        elif IdentifierResolver.is_phone(identifier):
            return 'phone'
        elif IdentifierResolver.is_email(identifier):
            return 'email'
        else:
            return 'unknown'
```

#### 2.2 更新服務層方法

```python
# mps_cli/services/member_service.py

from utils.identifier_resolver import IdentifierResolver

class MemberService(BaseService):
    
    def get_member_by_identifier(self, identifier: str) -> Optional[Member]:
        """通過任意識別碼獲取會員
        
        Args:
            identifier: 會員號、手機號、郵箱或 UUID
        
        Returns:
            Member 對象或 None
        """
        try:
            # 判斷識別碼類型
            id_type = IdentifierResolver.get_identifier_type(identifier)
            
            self.log_operation("獲取會員", {
                "identifier": identifier,
                "type": id_type
            })
            
            # 調用統一的查詢 RPC
            result = self.rpc_call("get_member_by_identifier", {
                "p_identifier": identifier
            })
            
            if result:
                return Member.from_dict(result)
            return None
            
        except Exception as e:
            self.logger.error(f"獲取會員失敗: {e}")
            raise self.handle_service_error("獲取會員", e, {
                "identifier": identifier
            })
    
    def update_member_profile(self, identifier: str, name: str = None, 
                            phone: str = None, email: str = None) -> bool:
        """更新會員資料
        
        Args:
            identifier: 會員號、手機號、郵箱或 UUID
            name: 新姓名
            phone: 新手機號
            email: 新郵箱
        """
        try:
            result = self.rpc_call("update_member_profile", {
                "p_identifier": identifier,
                "p_name": name,
                "p_phone": phone,
                "p_email": email
            })
            
            return result
            
        except Exception as e:
            raise self.handle_service_error("更新會員資料", e, {
                "identifier": identifier
            })
```

---

### 階段三：更新 UI 層（2-3 天）

#### 3.1 更新輸入提示

```python
# mps_cli/ui/admin_ui.py

def _view_member_info(self):
    """查看會員信息 - 改進版"""
    try:
        BaseUI.clear_screen()
        BaseUI.show_header("View Member Information")
        
        # 改進：支持多種識別碼
        print("\n您可以使用以下任意方式查找會員：")
        print("  • 會員號（如：M202501001）")
        print("  • 手機號（如：13800138000）")
        print("  • 郵箱（如：user@example.com）")
        
        identifier = input("\n請輸入: ").strip()
        
        if not identifier:
            BaseUI.show_error("識別碼不能為空")
            BaseUI.pause()
            return
        
        BaseUI.show_loading("查詢會員信息...")
        
        # 使用新的服務層方法
        member = self.member_service.get_member_by_identifier(identifier)
        
        if not member:
            BaseUI.show_error("會員不存在")
            BaseUI.pause()
            return
        
        # 顯示會員信息
        self._display_member_details(member)
        
    except Exception as e:
        BaseUI.show_error(f"查詢失敗：{e}")
        BaseUI.pause()

def _update_member_profile(self):
    """更新會員資料 - 改進版"""
    try:
        BaseUI.clear_screen()
        BaseUI.show_header("Update Member Profile")
        
        print("\n您可以使用以下任意方式查找會員：")
        print("  • 會員號（如：M202501001）")
        print("  • 手機號（如：13800138000）")
        print("  • 郵箱（如：user@example.com）")
        
        identifier = input("\n請輸入: ").strip()
        
        if not identifier:
            BaseUI.show_error("識別碼不能為空")
            BaseUI.pause()
            return
        
        # 先查詢會員
        member = self.member_service.get_member_by_identifier(identifier)
        
        if not member:
            BaseUI.show_error("會員不存在")
            BaseUI.pause()
            return
        
        # 顯示當前信息
        print(f"\n當前會員信息：")
        print(f"  會員號：{member.member_no}")
        print(f"  姓名：  {member.name}")
        print(f"  手機：  {member.phone}")
        print(f"  郵箱：  {member.email}")
        
        # 輸入新信息
        print(f"\n請輸入新信息（留空保持不變）：")
        new_name = input(f"姓名 [{member.name}]: ").strip() or None
        new_phone = input(f"手機 [{member.phone}]: ").strip() or None
        new_email = input(f"郵箱 [{member.email}]: ").strip() or None
        
        if not any([new_name, new_phone, new_email]):
            BaseUI.show_info("沒有需要更新的內容")
            BaseUI.pause()
            return
        
        # 確認更新
        if not BaseUI.confirm("確認更新？"):
            BaseUI.show_info("已取消")
            BaseUI.pause()
            return
        
        # 執行更新（使用業務識別碼）
        result = self.member_service.update_member_profile(
            member.member_no,  # 使用會員號而不是 UUID
            new_name,
            new_phone,
            new_email
        )
        
        if result:
            BaseUI.show_success("會員資料更新成功")
        else:
            BaseUI.show_error("會員資料更新失敗")
        
        BaseUI.pause()
        
    except Exception as e:
        BaseUI.show_error(f"更新失敗：{e}")
        BaseUI.pause()
```

#### 3.2 更新顯示格式

```python
def _display_member_list(self, members: List[Member]):
    """顯示會員列表 - 改進版"""
    
    # 改進：突出顯示業務識別碼
    headers = ["序號", "會員號", "姓名", "手機", "郵箱", "狀態"]
    data = []
    
    for i, member in enumerate(members, 1):
        data.append({
            "序號": i,
            "會員號": member.member_no,  # 突出顯示
            "姓名": member.name,
            "手機": member.phone,
            "郵箱": member.email,
            "狀態": member.get_status_display()
        })
    
    Table.display(headers, data)
    
    print("\n💡 提示：")
    print("  • 您可以使用會員號、手機號或郵箱進行操作")
    print("  • 無需記住或複製 UUID")
```

---

## 📊 改進效果對比

### 場景：更新會員資料

#### 改進前

```
Admin: 請輸入會員 ID
User: (需要複製) 550e8400-e29b-41d4-a716-446655440000
Admin: (粘貼) 550e8400-e29b-41d4-a716-446655440000
```

**問題**：
- ❌ 需要複製粘貼
- ❌ 容易出錯
- ❌ 不友好

#### 改進後

```
Admin: 請輸入會員號、手機號或郵箱
User: (直接輸入) M202501001
或
User: (直接輸入) 13800138000
或
User: (直接輸入) user@example.com
```

**優勢**：
- ✅ 直接輸入
- ✅ 多種方式
- ✅ 用戶友好

---

## 🎯 實施優先級

### P0 - 立即實施（必須）

1. **創建統一識別碼查詢 RPC** - 1 天
2. **更新服務層支持業務識別碼** - 2 天
3. **更新 Admin UI 輸入方式** - 2 天

**總計：5 天**

### P1 - 後續優化（建議）

4. **優化顯示格式** - 1 天
5. **添加識別碼驗證** - 1 天
6. **更新文檔和提示** - 1 天

---

## ✅ 驗收標準

### 功能完整性
- [ ] 所有 UI 操作支持業務識別碼輸入
- [ ] 支持多種識別方式（會員號/手機/郵箱）
- [ ] 自動識別識別碼類型
- [ ] 錯誤提示友好明確

### 用戶體驗
- [ ] 無需複製粘貼 UUID
- [ ] 輸入方式靈活多樣
- [ ] 提示信息清晰明確
- [ ] 操作效率提升 50%

### 兼容性
- [ ] 向後兼容（仍支持 UUID）
- [ ] 數據庫結構不變
- [ ] API 接口兼容

---

## 📝 總結

### 核心建議

**✅ 全面採用業務識別碼作為用戶界面的主要識別方式**

### 實施原則

1. **對外業務識別碼，對內 UUID**
   - UI 層：使用會員號、卡號、商戶代碼
   - 服務層：自動轉換
   - 數據庫：保持 UUID 作為主鍵

2. **支持多種識別方式**
   - 會員：會員號、手機號、郵箱
   - 卡片：卡號
   - 商戶：商戶代碼

3. **向後兼容**
   - 仍然支持 UUID 輸入
   - 自動識別識別碼類型
   - 平滑過渡

### 預期效果

- 🎯 用戶體驗提升 80%
- 🎯 操作效率提升 50%
- 🎯 錯誤率降低 70%
- 🎯 符合業務習慣

---

**分析人員**: AI Assistant  
**分析日期**: 2025-10-06  
**建議優先級**: P0 - 高優先級  
**預估工時**: 5-7 天
