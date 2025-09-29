# MPS Python CLI 實現路線圖

## 📋 功能模組詳細規劃

### 🎯 基於現有 RPC 的功能映射

#### 📊 RPC 函數與 UI 功能對應表

| UI 功能 | 角色 | 對應 RPC | 輸入參數 | 輸出結果 | 實現優先級 |
|---------|------|----------|----------|----------|------------|
| **會員註冊** | 管理員 | `create_member_profile` | 姓名、手機、郵箱、外部身份 | member_id | P0 |
| **生成付款碼** | 會員 | `rotate_card_qr` | card_id, ttl_seconds | qr_plain, expires_at | P0 |
| **掃碼收款** | 商戶 | `merchant_charge_by_qr` | 商戶碼、QR碼、金額 | 交易結果 | P0 |
| **卡片充值** | 會員 | `user_recharge_card` | card_id, 金額, 支付方式 | 交易結果 | P0 |
| **退款處理** | 商戶 | `merchant_refund_tx` | 商戶碼、原交易號、退款金額 | 退款結果 | P1 |
| **綁定卡片** | 會員 | `bind_member_to_card` | card_id, member_id, 角色, 密碼 | 綁定結果 | P1 |
| **凍結卡片** | 管理員 | `freeze_card` | card_id | 操作結果 | P1 |
| **調整積分** | 管理員 | `update_points_and_level` | card_id, 積分變化, 原因 | 操作結果 | P2 |
| **會員交易記錄** | 會員 | `get_member_transactions` | member_id, 分頁參數 | 交易列表 | P2 |
| **商戶交易記錄** | 商戶 | `get_merchant_transactions` | merchant_id, 分頁參數 | 交易列表 | P2 |
| **生成結算** | 商戶 | `generate_settlement` | merchant_id, 模式, 時間範圍 | settlement_id | P2 |
| **批量QR輪換** | 管理員 | `cron_rotate_qr_tokens` | ttl_seconds | 影響數量 | P3 |

**優先級說明**:
- P0: 核心功能，第一階段必須實現
- P1: 重要功能，第二階段實現
- P2: 增強功能，第三階段實現
- P3: 可選功能，後續版本實現

---

## 🏗️ 詳細實現計劃

### 第一階段：核心 MVP (2週)

#### Week 1: 基礎架構 + 會員功能

**Day 1-2: 項目搭建**
```bash
# 創建項目結構
mkdir mps_cli
cd mps_cli

# 創建目錄結構
mkdir -p config models services ui/components utils tests

# 創建基礎文件
touch main.py requirements.txt .env.example README.md
touch config/{__init__.py,settings.py,supabase_client.py,constants.py}
touch models/{__init__.py,base.py,member.py,card.py,transaction.py}
touch services/{__init__.py,base_service.py,member_service.py,payment_service.py}
touch ui/{__init__.py,base_ui.py,member_ui.py}
touch ui/components/{__init__.py,menu.py,table.py,form.py}
touch utils/{__init__.py,validators.py,formatters.py,error_handler.py,logger.py}
```

**實現清單**:
- [x] 項目結構搭建
- [x] 配置管理系統 (`settings.py`)
- [x] Supabase 客戶端封裝 (`supabase_client.py`)
- [x] 常量定義 (`constants.py`)
- [x] 基礎數據模型 (`base.py`, `member.py`, `card.py`)

**Day 3-4: UI 組件庫**
- [x] 基礎 UI 組件 (`base_ui.py`)
- [x] 菜單組件 (`menu.py`)
- [x] 表格組件 (`table.py`)
- [x] 表單組件 (`form.py`)
- [x] 工具函數 (`validators.py`, `formatters.py`, `error_handler.py`)

**Day 5-7: 會員功能實現**
- [x] 會員服務層 (`member_service.py`)
- [x] 會員 UI 界面 (`member_ui.py`)
- [x] 查看卡片功能
- [x] 生成 QR 碼功能
- [x] 卡片充值功能

#### Week 2: 商戶功能 + 管理功能

**Day 8-10: 商戶功能**
- [x] 支付服務層 (`payment_service.py`)
- [x] QR 服務層 (`qr_service.py`)
- [x] 商戶 UI 界面 (`merchant_ui.py`)
- [x] 掃碼收款功能
- [x] 退款處理功能

**Day 11-14: 管理功能**
- [x] 管理服務層 (`admin_service.py`)
- [x] 管理員 UI 界面 (`admin_ui.py`)
- [x] 創建會員功能
- [x] 卡片管理功能
- [x] 主入口程序 (`main.py`)

---

## 🔧 具體實現細節

### 1. 核心業務流程實現

#### 會員登入流程
```python
# ui/member_ui.py - _member_login 方法
def _member_login(self) -> bool:
    """會員登入流程"""
    print("┌─────────────────────────────────────┐")
    print("│            會員系統登入             │")
    print("└─────────────────────────────────────┘")
    
    # 輸入會員 ID 或手機號
    identifier = input("請輸入會員 ID 或手機號: ")
    
    try:
        # 嘗試按 ID 查詢
        if self._is_uuid(identifier):
            members = self.member_service.query_table("member_profiles", {"id": identifier})
        else:
            # 按手機號查詢
            members = self.member_service.query_table("member_profiles", {"phone": identifier})
        
        if not members:
            print("❌ 會員不存在")
            return False
        
        member = members[0]
        if member["status"] != "active":
            print(f"❌ 會員狀態異常: {member['status']}")
            return False
        
        self.current_member_id = member["id"]
        self.current_member_name = member["name"]
        
        print(f"✅ 登入成功！歡迎 {member['name']}")
        input("按任意鍵繼續...")
        return True
        
    except Exception as e:
        print(f"❌ 登入失敗: {e}")
        return False
```

#### 掃碼收款流程
```python
# ui/merchant_ui.py - _scan_and_charge 方法
def _scan_and_charge(self):
    """掃碼收款完整流程"""
    print("┌─────────────────────────────────────┐")
    print("│              掃碼收款               │")
    print("└─────────────────────────────────────┘")
    
    # Step 1: 獲取 QR 碼
    qr_plain = input("請掃描客戶 QR 碼 (或手動輸入): ")
    if not qr_plain.strip():
        print("❌ QR 碼不能為空")
        input("按任意鍵返回...")
        return
    
    # Step 2: 驗證 QR 碼（可選，提前驗證用戶體驗更好）
    try:
        card_id = self.qr_service.validate_qr(qr_plain)
        print(f"✅ QR 碼有效，卡片 ID: {card_id[:8]}...")
    except Exception as e:
        print(f"❌ QR 碼無效: {e}")
        input("按任意鍵返回...")
        return
    
    # Step 3: 輸入收款金額
    while True:
        try:
            amount_str = input("請輸入收款金額: ¥")
            amount = float(amount_str)
            if amount <= 0:
                print("❌ 金額必須大於 0")
                continue
            if amount > 50000:  # 設置合理上限
                print("❌ 單筆金額不能超過 ¥50,000")
                continue
            break
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    # Step 4: 顯示收款確認信息
    print(f"\n┌─────────────────────────────────────┐")
    print(f"│            收款信息確認             │")
    print(f"├─────────────────────────────────────┤")
    print(f"│ 商戶: {self.current_merchant_name:<25} │")
    print(f"│ 金額: {Formatter.format_currency(amount):<25} │")
    print(f"│ 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<21} │")
    print(f"└─────────────────────────────────────┘")
    
    if not input("確認收款？(y/n): ").lower() == 'y':
        print("❌ 收款已取消")
        input("按任意鍵返回...")
        return
    
    # Step 5: 執行收款
    try:
        print("💳 正在處理收款...")
        
        result = self.payment_service.charge_by_qr(
            self.current_merchant_code,
            qr_plain,
            Decimal(str(amount)),
            tag={"source": "pos_cli", "operator": self.current_operator}
        )
        
        # Step 6: 顯示收款結果
        self._show_payment_success(result, amount)
        
    except Exception as e:
        self._handle_payment_error(e)
    
    input("按任意鍵返回...")

def _show_payment_success(self, result: Dict, original_amount: float):
    """顯示收款成功界面"""
    print("┌─────────────────────────────────────┐")
    print("│              收款成功               │")
    print("├─────────────────────────────────────┤")
    print(f"│ 交易號: {result['tx_no']:<23} │")
    print(f"│ 原金額: {Formatter.format_currency(original_amount):<23} │")
    print(f"│ 折扣率: {Formatter.format_percentage(result['discount']):<23} │")
    print(f"│ 實收金額: {Formatter.format_currency(result['final_amount']):<21} │")
    print(f"│ 時間: {datetime.now().strftime('%H:%M:%S'):<27} │")
    print("├─────────────────────────────────────┤")
    print("│ 🎉 收款成功，感謝您的使用！         │")
    print("└─────────────────────────────────────┘")

def _handle_payment_error(self, error: Exception):
    """處理支付錯誤"""
    error_str = str(error)
    
    print("┌─────────────────────────────────────┐")
    print("│              收款失敗               │")
    print("├─────────────────────────────────────┤")
    
    if "INSUFFICIENT_BALANCE" in error_str:
        print("│ ❌ 客戶餘額不足                    │")
        print("│ 💡 建議：提醒客戶充值或使用其他卡片 │")
    elif "QR_EXPIRED_OR_INVALID" in error_str:
        print("│ ❌ QR 碼已過期或無效               │")
        print("│ 💡 建議：請客戶重新生成付款碼       │")
    elif "NOT_MERCHANT_USER" in error_str:
        print("│ ❌ 您沒有此商戶的操作權限           │")
        print("│ 💡 建議：聯繫管理員檢查權限設置     │")
    else:
        print(f"│ ❌ 系統錯誤: {error_str[:25]:<25} │")
        print("│ 💡 建議：稍後重試或聯繫技術支持     │")
    
    print("└─────────────────────────────────────┘")
```

### 2. 數據查詢與展示

#### 交易記錄查詢實現
```python
# services/query_service.py
class QueryService(BaseService):
    def get_member_transactions_paginated(self, member_id: str, page: int = 0, 
                                        page_size: int = 20) -> Dict:
        """分頁查詢會員交易記錄"""
        offset = page * page_size
        
        result = self.rpc_call("get_member_transactions", {
            "p_member_id": member_id,
            "p_limit": page_size,
            "p_offset": offset
        })
        
        total_count = result[0].get('total_count', 0) if result else 0
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "data": result,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages - 1,
                "has_prev": page > 0
            }
        }
    
    def get_merchant_daily_summary(self, merchant_id: str, date: str) -> Dict:
        """獲取商戶日交易摘要"""
        from datetime import datetime
        
        start_time = f"{date}T00:00:00Z"
        end_time = f"{date}T23:59:59Z"
        
        transactions = self.rpc_call("get_merchant_transactions", {
            "p_merchant_id": merchant_id,
            "p_limit": 1000,  # 假設單日不超過1000筆
            "p_offset": 0,
            "p_start_date": start_time,
            "p_end_date": end_time
        })
        
        # 統計計算
        summary = {
            "date": date,
            "total_count": 0,
            "payment_count": 0,
            "refund_count": 0,
            "payment_amount": 0,
            "refund_amount": 0,
            "net_amount": 0
        }
        
        for tx in transactions:
            summary["total_count"] += 1
            if tx["tx_type"] == "payment":
                summary["payment_count"] += 1
                summary["payment_amount"] += tx["final_amount"]
            elif tx["tx_type"] == "refund":
                summary["refund_count"] += 1
                summary["refund_amount"] += tx["final_amount"]
        
        summary["net_amount"] = summary["payment_amount"] - summary["refund_amount"]
        
        return summary
```

#### 分頁顯示組件
```python
# ui/components/paginated_table.py
class PaginatedTable(Table):
    def __init__(self, headers: List[str], data_fetcher: Callable, 
                 title: Optional[str] = None, page_size: int = 20):
        self.headers = headers
        self.data_fetcher = data_fetcher
        self.title = title
        self.page_size = page_size
        self.current_page = 0
    
    def display_interactive(self):
        """交互式分頁顯示"""
        while True:
            # 獲取當前頁數據
            result = self.data_fetcher(self.current_page, self.page_size)
            data = result.get("data", [])
            pagination = result.get("pagination", {})
            
            # 顯示表格
            super().__init__(self.headers, data, self.title)
            self.display()
            
            # 顯示分頁信息
            if pagination:
                print(f"第 {pagination['current_page'] + 1} 頁，共 {pagination['total_pages']} 頁")
                print(f"總計 {pagination['total_count']} 筆記錄")
            
            # 分頁控制
            if not data:
                print("📝 暫無數據")
                input("按任意鍵返回...")
                break
            
            actions = []
            if pagination.get("has_prev", False):
                actions.append("P-上一頁")
            if pagination.get("has_next", False):
                actions.append("N-下一頁")
            actions.append("Q-退出")
            
            if len(actions) > 1:
                action = input(f"{' | '.join(actions)}: ").upper()
                if action == "N" and pagination.get("has_next", False):
                    self.current_page += 1
                elif action == "P" and pagination.get("has_prev", False):
                    self.current_page -= 1
                elif action == "Q":
                    break
            else:
                input("按任意鍵返回...")
                break
```

### 3. 錯誤處理與用戶體驗

#### 統一錯誤處理
```python
# utils/error_handler.py - 增強版
class EnhancedErrorHandler(ErrorHandler):
    def __init__(self):
        super().__init__()
        self.error_context = {}
    
    def handle_with_context(self, error: Exception, context: Dict[str, Any]) -> str:
        """帶上下文的錯誤處理"""
        self.error_context = context
        error_str = str(error)
        
        # 根據上下文提供更精確的錯誤信息
        if "INSUFFICIENT_BALANCE" in error_str:
            card_id = context.get("card_id")
            if card_id:
                # 查詢當前餘額
                try:
                    cards = self.query_table("member_cards", {"id": card_id})
                    if cards:
                        balance = cards[0]["balance"]
                        return f"❌ 餘額不足，當前餘額: {Formatter.format_currency(balance)}"
                except:
                    pass
            return "❌ 餘額不足，請充值後再試"
        
        elif "QR_EXPIRED_OR_INVALID" in error_str:
            return "❌ QR 碼已過期或無效，請重新生成付款碼"
        
        # 其他錯誤處理...
        return super().handle_rpc_error(error)
    
    def suggest_solution(self, error_code: str) -> Optional[str]:
        """提供解決方案建議"""
        solutions = {
            "INSUFFICIENT_BALANCE": "建議客戶充值或使用其他卡片",
            "QR_EXPIRED_OR_INVALID": "請客戶重新生成付款碼",
            "CARD_NOT_FOUND_OR_INACTIVE": "請檢查卡片狀態或聯繫客服",
            "NOT_MERCHANT_USER": "請聯繫管理員檢查商戶權限",
            "REFUND_EXCEEDS_REMAINING": "請檢查原交易的可退金額"
        }
        
        return solutions.get(error_code)
```

#### 用戶輸入增強
```python
# ui/components/enhanced_input.py
class EnhancedInput:
    @staticmethod
    def get_amount_input(prompt: str, min_amount: float = 0.01, 
                        max_amount: float = 50000) -> float:
        """增強的金額輸入"""
        while True:
            try:
                amount_str = input(f"{prompt} (¥{min_amount:.2f} - ¥{max_amount:.2f}): ¥")
                amount = float(amount_str)
                
                if amount < min_amount:
                    print(f"❌ 金額不能小於 ¥{min_amount:.2f}")
                    continue
                if amount > max_amount:
                    print(f"❌ 金額不能超過 ¥{max_amount:.2f}")
                    continue
                
                return amount
                
            except ValueError:
                print("❌ 請輸入有效的數字")
            except KeyboardInterrupt:
                raise
    
    @staticmethod
    def get_qr_input(prompt: str = "請輸入 QR 碼") -> str:
        """QR 碼輸入驗證"""
        while True:
            qr_code = input(f"{prompt}: ").strip()
            
            if not qr_code:
                print("❌ QR 碼不能為空")
                continue
            
            if len(qr_code) < 16:
                print("❌ QR 碼格式不正確（長度不足）")
                continue
            
            return qr_code
    
    @staticmethod
    def get_confirmation(message: str, default: bool = False) -> bool:
        """獲取確認輸入"""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} ({default_text}): ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '是', '確認']
```

---

## 📊 測試策略

### 🧪 測試計劃

#### 單元測試
```python
# tests/test_services.py
import unittest
from unittest.mock import Mock, patch
from services.payment_service import PaymentService
from decimal import Decimal

class TestPaymentService(unittest.TestCase):
    def setUp(self):
        self.payment_service = PaymentService()
        self.payment_service.client = Mock()
    
    def test_charge_by_qr_success(self):
        """測試掃碼支付成功"""
        # Mock RPC 返回
        mock_result = [{
            "tx_id": "test-tx-id",
            "tx_no": "PAY0000000001",
            "final_amount": 95.0,
            "discount": 0.95
        }]
        self.payment_service.client.rpc.return_value = mock_result
        
        # 執行測試
        result = self.payment_service.charge_by_qr(
            "TEST001", "test-qr-code", Decimal("100.00")
        )
        
        # 驗證結果
        self.assertEqual(result["tx_no"], "PAY0000000001")
        self.assertEqual(result["final_amount"], 95.0)
    
    def test_charge_by_qr_insufficient_balance(self):
        """測試餘額不足錯誤"""
        # Mock RPC 拋出異常
        self.payment_service.client.rpc.side_effect = Exception("INSUFFICIENT_BALANCE")
        
        # 執行測試並驗證異常
        with self.assertRaises(Exception) as context:
            self.payment_service.charge_by_qr(
                "TEST001", "test-qr-code", Decimal("1000.00")
            )
        
        self.assertIn("餘額不足", str(context.exception))
```

#### 集成測試
```python
# tests/test_integration.py
import unittest
from config.supabase_client import SupabaseClient
from services.member_service import MemberService

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # 使用測試數據庫
        os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
        self.member_service = MemberService()
    
    def test_create_member_flow(self):
        """測試創建會員完整流程"""
        # 創建測試會員
        member_id = self.member_service.create_member(
            name="測試用戶",
            phone="13800000001",
            email="test@example.com"
        )
        
        self.assertIsNotNone(member_id)
        
        # 驗證會員創建成功
        members = self.member_service.query_table("member_profiles", {"id": member_id})
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["name"], "測試用戶")
        
        # 驗證自動生成標準卡
        cards = self.member_service.get_member_cards(member_id)
        standard_cards = [card for card in cards if card.card_type == "standard"]
        self.assertEqual(len(standard_cards), 1)
```

---

## 🚀 部署與分發

### 📦 打包配置

#### setup.py
```python
from setuptools import setup, find_packages

setup(
    name="mps-cli",
    version="1.0.0",
    description="MPS Member Payment System CLI Application",
    author="MPS Team",
    author_email="dev@mps.example.com",
    packages=find_packages(),
    install_requires=[
        "supabase>=2.3.4",
        "python-dotenv>=1.0.0",
        "rich>=13.7.0",
        "click>=8.1.7",
        "pydantic>=2.5.2"
    ],
    entry_points={
        "console_scripts": [
            "mps-member=main:member_main",
            "mps-merchant=main:merchant_main",
            "mps-admin=main:admin_main",
            "mps=main:main"
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ]
)
```

#### 構建腳本
```bash
#!/bin/bash
# scripts/build.sh

echo "🔨 Building MPS CLI Application..."

# 清理舊的構建文件
rm -rf build/ dist/ *.egg-info/

# 安裝構建依賴
pip install build wheel

# 構建包
python -m build

# 創建可執行文件 (使用 PyInstaller)
pip install pyinstaller
pyinstaller --onefile --name mps-cli main.py

echo "✅ Build completed!"
echo "📦 Distribution files:"
ls -la dist/
```

---

## 📋 實現檢查清單

### ✅ 第一階段檢查清單 (MVP)

#### 基礎架構
- [ ] 項目結構創建完成
- [ ] 配置管理系統實現
- [ ] Supabase 客戶端封裝
- [ ] 錯誤處理機制
- [ ] 基礎 UI 組件庫

#### 會員功能
- [ ] 會員登入驗證
- [ ] 查看卡片列表
- [ ] 生成付款 QR 碼
- [ ] 卡片充值功能
- [ ] 基本錯誤處理

#### 商戶功能
- [ ] 商戶登入驗證
- [ ] 掃碼收款功能
- [ ] 收款結果顯示
- [ ] 基本錯誤處理

#### 管理功能
- [ ] 管理員登入驗證
- [ ] 創建會員功能
- [ ] 卡片凍結功能
- [ ] 基本操作確認

### 🚀 第二階段檢查清單 (完整功能)

#### 查詢功能
- [ ] 會員交易記錄查詢
- [ ] 商戶交易記錄查詢
- [ ] 交易詳情查詢
- [ ] 分頁顯示支持

#### 結算功能
- [ ] 商戶結算生成
- [ ] 結算歷史查詢
- [ ] 結算報表顯示

#### 高級管理
- [ ] 積分手動調整
- [ ] 批量 QR 碼輪換
- [ ] 會員狀態管理
- [ ] 商戶狀態管理

#### UI 增強
- [ ] 數據格式化美化
- [ ] 操作確認對話框
- [ ] 進度指示器
- [ ] 幫助信息顯示

---

## 🎯 成功標準

### 功能完整性
- 所有 P0 功能 100% 實現
- 所有 P1 功能 90% 實現
- 核心業務流程無阻塞

### 用戶體驗
- 操作流程直觀易懂
- 錯誤提示清晰有用
- 響應時間 < 3 秒

### 代碼質量
- 單元測試覆蓋率 > 80%
- 代碼符合 PEP 8 規範
- 無嚴重安全漏洞

### 穩定性
- 連續運行 24 小時無崩潰
- 網絡異常自動恢復
- 數據操作事務安全

這個實現路線圖提供了完整的開發計劃，基於現有的 RPC 功能，創建一個實用的 Python 文字 UI 系統，既不會超出現有系統範疇，又能滿足實際業務需求。