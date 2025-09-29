# MPS CLI 適配指南

## 📋 概述

本文檔詳細說明如何將現有的 `mps_cli` 從直接調用 Supabase RPC 改為通過 `mps_api` 進行 HTTP API 調用。這個適配過程將大幅提升安全性，同時保持用戶體驗完全不變。

## 🎯 適配目標

### 主要目標
1. **安全性提升**：移除客戶端的 `service_role_key` 依賴
2. **功能保持**：所有現有功能完全保持不變
3. **用戶體驗**：UI 和操作流程完全一致
4. **可維護性**：代碼結構更清晰，易於維護

### 成功標準
- ✅ 所有 P0/P1 功能正常工作
- ✅ 用戶操作流程無變化
- ✅ 錯誤處理和提示保持一致
- ✅ 性能無明顯下降

---

## 🔄 詳細適配方案

### 📊 文件修改對照表

| 文件路徑 | 修改類型 | 修改程度 | 主要變更 | 預估工時 |
|----------|----------|----------|----------|----------|
| [`config/settings.py`](../../mps_cli/config/settings.py) | 配置修改 | 30% | 移除 Supabase 配置，添加 API 配置 | 1小時 |
| [`config/supabase_client.py`](../../mps_cli/config/supabase_client.py) | 重寫 | 100% | 改為 `api_client.py` | 4小時 |
| [`services/base_service.py`](../../mps_cli/services/base_service.py) | 方法修改 | 40% | `rpc_call` → `api_call` | 2小時 |
| [`services/member_service.py`](../../mps_cli/services/member_service.py) | 調用修改 | 20% | RPC 調用改為 HTTP 調用 | 1小時 |
| [`services/payment_service.py`](../../mps_cli/services/payment_service.py) | 調用修改 | 20% | RPC 調用改為 HTTP 調用 | 1小時 |
| [`services/merchant_service.py`](../../mps_cli/services/merchant_service.py) | 調用修改 | 20% | RPC 調用改為 HTTP 調用 | 1小時 |
| [`services/admin_service.py`](../../mps_cli/services/admin_service.py) | 調用修改 | 20% | RPC 調用改為 HTTP 調用 | 1小時 |
| [`services/qr_service.py`](../../mps_cli/services/qr_service.py) | 調用修改 | 20% | RPC 調用改為 HTTP 調用 | 1小時 |
| [`ui/member_ui.py`](../../mps_cli/ui/member_ui.py) | 登入修改 | 10% | 添加 API 登入邏輯 | 0.5小時 |
| [`ui/merchant_ui.py`](../../mps_cli/ui/merchant_ui.py) | 登入修改 | 10% | 添加 API 登入邏輯 | 0.5小時 |
| [`ui/admin_ui.py`](../../mps_cli/ui/admin_ui.py) | 登入修改 | 10% | 添加 API 登入邏輯 | 0.5小時 |
| [`main.py`](../../mps_cli/main.py) | 測試修改 | 15% | 連接測試改為 API 測試 | 0.5小時 |

**總工作量：約 13.5 小時 (1.7 天)**

---

## 🔧 具體修改實施

### 1. 配置層適配

#### 修改 config/settings.py

```python
# 修改前
@dataclass
class DatabaseConfig:
    url: str
    service_role_key: str
    anon_key: str
    timeout: int = 30

class Settings:
    def __init__(self):
        self.database = DatabaseConfig(
            url=os.getenv("SUPABASE_URL", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", "")
        )

# 修改後
@dataclass
class APIConfig:
    base_url: str
    timeout: int = 30
    retry_count: int = 3
    max_retries: int = 3

class Settings:
    def __init__(self):
        self.api = APIConfig(
            base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
            timeout=int(os.getenv("API_TIMEOUT", "30")),
            retry_count=int(os.getenv("API_RETRY_COUNT", "3"))
        )
        
        # 保留 UI 和日誌配置不變
        self.ui = UIConfig(...)
        self.logging = LogConfig(...)
    
    def validate(self) -> bool:
        """驗證配置完整性"""
        if not self.api.base_url:
            raise ValueError("API_BASE_URL 是必需的")
        return True
```

#### 新增 config/api_client.py

```python
import requests
import json
import time
from typing import Dict, Any, Optional
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class APIClient:
    """API 客戶端"""
    
    def __init__(self):
        self.base_url = settings.api.base_url.rstrip('/')
        self.timeout = settings.api.timeout
        self.retry_count = settings.api.retry_count
        self.session_token: Optional[str] = None
        self.session_info: Optional[Dict] = None
        self.token_expires_at: Optional[float] = None
    
    def login(self, role: str, identifier: str, **kwargs) -> bool:
        """登入並獲取 Session Token"""
        try:
            payload = {
                "role": role,
                "identifier": identifier
            }
            
            # 添加角色特定的額外參數
            if role == "merchant" and "operator" in kwargs:
                payload["operator"] = kwargs["operator"]
            elif role == "admin" and "admin_code" in kwargs:
                payload["admin_code"] = kwargs["admin_code"]
            
            logger.info(f"嘗試 API 登入: {role}, {identifier}")
            
            response = self._make_request("POST", "/auth/login", payload)
            
            if response and response.get("success"):
                self.session_token = response["token"]
                self.session_info = response["user_info"]
                
                # 解析過期時間
                expires_at = response.get("expires_at")
                if expires_at:
                    from datetime import datetime
                    expire_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    self.token_expires_at = expire_dt.timestamp()
                
                logger.info(f"API 登入成功: {role}, 用戶: {self.session_info.get('name')}")
                return True
            else:
                error_msg = response.get("error", "登入失敗") if response else "無響應"
                logger.warning(f"API 登入失敗: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"API 登入異常: {e}")
            return False
    
    def logout(self) -> bool:
        """登出"""
        try:
            if self.session_token:
                self._make_request("POST", "/auth/logout")
            
            self._clear_session()
            logger.info("API 登出成功")
            return True
            
        except Exception as e:
            logger.error(f"API 登出失敗: {e}")
            self._clear_session()  # 強制清除本地 session
            return False
    
    def call_api(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """調用 API"""
        # 檢查 token 是否過期
        if self._is_token_expired():
            raise Exception("認證已過期，請重新登入")
        
        return self._make_request(method, endpoint, data, include_auth=True)
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     include_auth: bool = False) -> Dict:
        """發起 HTTP 請求"""
        headers = {"Content-Type": "application/json"}
        
        if include_auth and self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retry_count + 1):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=data, timeout=self.timeout)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
                elif method.upper() == "PUT":
                    response = requests.put(url, headers=headers, json=data, timeout=self.timeout)
                elif method.upper() == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=self.timeout)
                else:
                    raise ValueError(f"不支持的 HTTP 方法: {method}")
                
                # 處理響應
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    self._clear_session()
                    raise Exception("認證已過期，請重新登入")
                elif response.status_code == 403:
                    raise Exception("權限不足")
                elif response.status_code == 404:
                    raise Exception("資源不存在")
                elif response.status_code == 500:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("detail", "服務器內部錯誤")
                    raise Exception(f"服務器錯誤: {error_msg}")
                else:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("detail", f"HTTP {response.status_code}")
                    raise Exception(f"API 調用失敗: {error_msg}")
                    
            except requests.exceptions.Timeout:
                if attempt < self.retry_count:
                    logger.warning(f"API 調用超時，重試 {attempt + 1}/{self.retry_count}")
                    time.sleep(1)
                    continue
                raise Exception("API 調用超時")
            except requests.exceptions.ConnectionError:
                if attempt < self.retry_count:
                    logger.warning(f"API 連接失敗，重試 {attempt + 1}/{self.retry_count}")
                    time.sleep(2)
                    continue
                raise Exception("無法連接到 API 服務")
            except Exception as e:
                if attempt < self.retry_count and "認證已過期" not in str(e):
                    logger.warning(f"API 調用失敗，重試 {attempt + 1}/{self.retry_count}: {e}")
                    time.sleep(1)
                    continue
                raise
    
    def _is_token_expired(self) -> bool:
        """檢查 token 是否過期"""
        if not self.session_token or not self.token_expires_at:
            return True
        
        return time.time() >= self.token_expires_at - 60  # 提前 1 分鐘過期
    
    def _clear_session(self):
        """清除 session 信息"""
        self.session_token = None
        self.session_info = None
        self.token_expires_at = None
    
    def is_authenticated(self) -> bool:
        """檢查是否已認證"""
        return self.session_token is not None and not self._is_token_expired()
    
    def get_current_user(self) -> Optional[Dict]:
        """獲取當前用戶信息"""
        return self.session_info
    
    def test_connection(self) -> bool:
        """測試 API 連接"""
        try:
            response = self._make_request("GET", "/health")
            return response.get("status") == "healthy"
        except Exception as e:
            logger.error(f"API 連接測試失敗: {e}")
            return False

# 全局 API 客戶端實例
api_client = APIClient()
```

### 2. 服務層適配

#### 修改 services/base_service.py

```python
# 修改前
from config.supabase_client import supabase_client
from utils.error_handler import error_handler

class BaseService(ABC):
    def __init__(self):
        self.client = supabase_client
        self.error_handler = error_handler
    
    def rpc_call(self, function_name: str, params: Dict[str, Any]) -> Any:
        """安全的 RPC 調用"""
        try:
            result = self.client.rpc(function_name, params)
            return result
        except Exception as e:
            raise self.error_handler.handle_rpc_error(e)

# 修改後
from config.api_client import api_client
from utils.error_handler import error_handler

class BaseService(ABC):
    def __init__(self):
        self.client = api_client
        self.error_handler = error_handler
    
    def api_call(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Any:
        """安全的 API 調用"""
        try:
            result = self.client.call_api(method, endpoint, data)
            return result
        except Exception as e:
            raise self.error_handler.handle_api_error(e)
    
    # 移除或適配原有的查詢方法
    def query_table(self, table: str, filters: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """查詢表格數據 - 需要根據具體需求適配為 API 調用"""
        # 這個方法可能需要移除，或者實現為特定的 API 調用
        raise NotImplementedError("請使用具體的 API 端點")
```

#### 修改 services/member_service.py

```python
# 修改前後對比示例

# 修改前 (直接 RPC 調用)
def create_member(self, name: str, phone: str, email: str, 
                 binding_user_org: Optional[str] = None,
                 binding_org_id: Optional[str] = None) -> str:
    params = {
        "p_name": name,
        "p_phone": phone,
        "p_email": email,
        "p_binding_user_org": binding_user_org,
        "p_binding_org_id": binding_org_id,
        "p_default_card_type": "standard"
    }
    
    member_id = self.rpc_call("create_member_profile", params)
    return member_id

# 修改後 (HTTP API 調用)
def create_member(self, name: str, phone: str, email: str,
                 binding_user_org: Optional[str] = None,
                 binding_org_id: Optional[str] = None) -> str:
    data = {
        "name": name,
        "phone": phone,
        "email": email,
        "binding_user_org": binding_user_org,
        "binding_org_id": binding_org_id,
        "default_card_type": "standard"
    }
    
    result = self.api_call("POST", "/admin/members", data)
    return result["member"]["member_id"]

# 修改前 (複雜的表查詢)
def get_member_cards(self, member_id: str) -> List[Card]:
    # 查詢會員擁有的卡片
    owned_cards = self.query_table("member_cards", {"owner_member_id": member_id})
    
    # 查詢會員綁定的共享卡片
    bindings = self.query_table("card_bindings", {"member_id": member_id})
    shared_card_ids = [b["card_id"] for b in bindings]
    
    shared_cards = []
    for card_id in shared_card_ids:
        cards = self.query_table("member_cards", {"id": card_id})
        if cards:
            shared_cards.extend(cards)
    
    # 合併並去重
    all_cards_data = owned_cards + shared_cards
    unique_cards = {card["id"]: card for card in all_cards_data}.values()
    
    return [Card.from_dict(card_data) for card_data in unique_cards]

# 修改後 (簡化的 API 調用)
def get_member_cards(self, member_id: str) -> List[Card]:
    result = self.api_call("GET", "/member/cards")
    cards_data = result.get("cards", [])
    return [Card.from_dict(card_data) for card_data in cards_data]
```

### 3. UI 層適配

#### 修改登入流程

```python
# ui/member_ui.py - 修改前後對比

# 修改前 (直接查詢數據庫)
def _member_login(self) -> bool:
    identifier = input("會員 ID/手機號: ").strip()
    
    try:
        member = self.member_service.validate_member_login(identifier)
        if member:
            self.current_member = member
            self.current_member_id = member.id
            return True
        return False
    except Exception as e:
        print(f"❌ 登入失敗: {e}")
        return False

# 修改後 (通過 API 登入)
def _member_login(self) -> bool:
    identifier = input("會員 ID/手機號: ").strip()
    
    try:
        # 通過 API 客戶端登入
        if self.client.login("member", identifier):
            user_info = self.client.get_current_user()
            self.current_member_id = user_info["id"]
            self.current_member_name = user_info["name"]
            return True
        return False
    except Exception as e:
        print(f"❌ 登入失敗: {e}")
        return False
```

### 4. 錯誤處理適配

#### 修改 utils/error_handler.py

```python
# 添加 API 錯誤處理方法
def handle_api_error(self, error: Exception) -> Exception:
    """處理 API 錯誤"""
    error_str = str(error)
    
    # 處理 API 特定錯誤
    if "認證已過期" in error_str:
        return Exception("登入已過期，請重新登入")
    elif "權限不足" in error_str:
        return Exception("您沒有執行此操作的權限")
    elif "無法連接到 API 服務" in error_str:
        return Exception("網絡連接失敗，請檢查網絡或聯繫技術支持")
    elif "API 調用超時" in error_str:
        return Exception("請求超時，請稍後重試")
    
    # 嘗試解析 API 返回的業務錯誤
    try:
        if "服務器錯誤:" in error_str:
            # 提取服務器返回的具體錯誤
            server_error = error_str.split("服務器錯誤:")[-1].strip()
            return self.handle_rpc_error(Exception(server_error))
    except:
        pass
    
    # 默認處理
    return Exception(f"操作失敗: {error_str}")
```

---

## 📋 逐步適配指南

### 🗓️ 適配時程安排

#### 第一天：基礎設施適配 (6小時)

**上午 (3小時)**：
1. **配置層修改** (1小時)
   - 修改 [`config/settings.py`](../../mps_cli/config/settings.py)
   - 更新 [`.env.example`](../../mps_cli/.env.example)

2. **API 客戶端創建** (2小時)
   - 創建 `config/api_client.py`
   - 實現登入、登出、API 調用邏輯

**下午 (3小時)**：
3. **基礎服務適配** (2小時)
   - 修改 [`services/base_service.py`](../../mps_cli/services/base_service.py)
   - 實現 `api_call` 方法

4. **錯誤處理適配** (1小時)
   - 修改 [`utils/error_handler.py`](../../mps_cli/utils/error_handler.py)
   - 添加 API 錯誤處理邏輯

#### 第二天：業務服務適配 (6小時)

**上午 (3小時)**：
1. **會員服務適配** (1小時)
   - 修改 [`services/member_service.py`](../../mps_cli/services/member_service.py)
   - 將 RPC 調用改為 HTTP API 調用

2. **支付服務適配** (1小時)
   - 修改 [`services/payment_service.py`](../../mps_cli/services/payment_service.py)
   - 適配充值和支付相關 API

3. **QR 服務適配** (1小時)
   - 修改 [`services/qr_service.py`](../../mps_cli/services/qr_service.py)
   - 適配 QR 碼生成和驗證 API

**下午 (3小時)**：
4. **商戶服務適配** (1小時)
   - 修改 [`services/merchant_service.py`](../../mps_cli/services/merchant_service.py)
   - 適配商戶交易相關 API

5. **管理員服務適配** (1小時)
   - 修改 [`services/admin_service.py`](../../mps_cli/services/admin_service.py)
   - 適配管理員操作 API

6. **UI 登入適配** (1小時)
   - 修改各 UI 文件的登入邏輯
   - 適配 Session 管理

#### 第三天：測試和優化 (2小時)

1. **功能測試** (1小時)
   - 測試所有 P0/P1 功能
   - 驗證用戶體驗一致性

2. **錯誤處理測試** (0.5小時)
   - 測試各種錯誤場景
   - 驗證錯誤提示友好性

3. **性能測試** (0.5小時)
   - 測試 API 調用性能
   - 優化超時和重試設置

---

## 🔧 關鍵適配技巧

### 1. RPC 參數到 HTTP 數據的轉換

```python
# RPC 調用模式
params = {
    "p_card_id": card_id,        # RPC 參數前綴 p_
    "p_amount": amount,
    "p_payment_method": method
}
result = self.rpc_call("user_recharge_card", params)

# HTTP API 調用模式  
data = {
    "card_id": card_id,          # 移除 p_ 前綴
    "amount": amount,
    "payment_method": method
}
result = self.api_call("POST", "/member/recharge", data)
```

### 2. 分頁數據處理

```python
# RPC 調用模式
def get_member_transactions(self, member_id: str, limit: int = 20, offset: int = 0):
    params = {"p_member_id": member_id, "p_limit": limit, "p_offset": offset}
    result = self.rpc_call("get_member_transactions", params)
    
    # 手動計算分頁信息
    total_count = result[0].get('total_count', 0) if result else 0
    # ... 分頁邏輯

# HTTP API 調用模式
def get_member_transactions(self, member_id: str, limit: int = 20, offset: int = 0):
    result = self.api_call("GET", f"/member/transactions?limit={limit}&offset={offset}")
    
    # API 已經包含完整的分頁信息
    return {
        "data": [Transaction.from_dict(tx) for tx in result["transactions"]],
        "pagination": result["pagination"]
    }
```

### 3. 錯誤信息映射

```python
# 統一的錯誤處理適配
def handle_service_error(self, operation: str, error: Exception, context: Dict = None):
    # API 錯誤通常已經是用戶友好的中文信息
    error_str = str(error)
    
    # 特殊錯誤處理
    if "認證已過期" in error_str:
        # 觸發重新登入流程
        self.client.logout()
        raise Exception("登入已過期，請重新登入")
    
    # 其他錯誤直接返回
    return Exception(error_str)
```

---

## 📊 適配驗證清單

### ✅ 功能驗證清單

#### 會員功能
- [ ] 會員登入 (ID/手機號)
- [ ] 查看卡片列表
- [ ] 生成付款 QR 碼
- [ ] 卡片充值
- [ ] 查看交易記錄
- [ ] 綁定新卡片
- [ ] 查看積分等級

#### 商戶功能
- [ ] 商戶登入 (商戶代碼)
- [ ] 掃碼收款
- [ ] 退款處理
- [ ] 查看今日交易
- [ ] 查看交易記錄
- [ ] 查看商戶信息

#### 管理員功能
- [ ] 管理員登入
- [ ] 創建新會員
- [ ] 凍結/解凍卡片
- [ ] 調整積分
- [ ] 暫停會員
- [ ] 搜索功能
- [ ] 系統統計
- [ ] 批量 QR 輪換

### ✅ 技術驗證清單

#### API 連接
- [ ] API 服務連接測試
- [ ] 認證 Token 獲取
- [ ] Token 過期處理
- [ ] 網絡異常處理

#### 數據一致性
- [ ] 所有 RPC 函數正確調用
- [ ] 數據格式保持一致
- [ ] 分頁功能正常
- [ ] 錯誤信息準確

#### 性能表現
- [ ] API 調用響應時間 < 1秒
- [ ] UI 響應無明顯延遲
- [ ] 大量數據加載正常
- [ ] 併發操作穩定

---

## 🚀 部署和配置

### 📦 部署準備

#### 1. API 服務部署
```bash
# 部署 mps_api 到服務器
cd mps_api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 或使用 Docker
docker build -t mps_api .
docker run -p 8000:8000 mps_api
```

#### 2. CLI 配置更新
```bash
# 更新 mps_cli/.env
API_BASE_URL=http://your-api-server:8000
API_TIMEOUT=30
API_RETRY_COUNT=3

# 移除 Supabase 配置
# SUPABASE_URL=...
# SUPABASE_SERVICE_ROLE_KEY=...
```

### 🔧 配置驗證

#### 連接測試
```bash
# 測試 API 連接
cd mps_cli
python main.py test

# 預期輸出
✅ API 連接成功
📊 系統概況:
  會員數量: 8567
  卡片數量: 12345
  商戶數量: 234
```

#### 功能測試
```bash
# 測試會員功能
python main.py member

# 測試商戶功能  
python main.py merchant

# 測試管理員功能
python main.py admin
```

---

## 📈 性能優化建議

### 1. API 調用優化

#### 批量請求
```python
# 避免多次 API 調用
# 不好的做法
cards = []
for card_id in card_ids:
    card = self.api_call("GET", f"/common/cards/{card_id}")
    cards.append(card)

# 好的做法
cards = self.api_call("POST", "/common/cards/batch", {"card_ids": card_ids})
```

#### 緩存機制
```python
# 在 API 客戶端添加簡單緩存
class APIClient:
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5分鐘
    
    def call_api_with_cache(self, method: str, endpoint: str, data: Dict = None):
        cache_key = f"{method}:{endpoint}:{hash(str(data))}"
        
        # 檢查緩存
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_data
        
        # 調用 API
        result = self.call_api(method, endpoint, data)
        
        # 緩存結果 (僅對 GET 請求)
        if method.upper() == "GET":
            self._cache[cache_key] = (result, time.time())
        
        return result
```

### 2. 錯誤恢復機制

```python
# 自動重新登入機制
def api_call_with_auto_reauth(self, method: str, endpoint: str, data: Dict = None):
    try:
        return self.api_call(method, endpoint, data)
    except Exception as e:
        if "認證已過期" in str(e):
            # 嘗試重新登入
            if self._auto_relogin():
                return self.api_call(method, endpoint, data)
        raise e

def _auto_relogin(self) -> bool:
    """自動重新登入"""
    if hasattr(self, '_last_login_info'):
        role, identifier, kwargs = self._last_login_info
        return self.login(role, identifier, **kwargs)
    return False
```

---

## 🎯 適配成功標準

### ✅ 功能完整性
- 所有 P0 功能 100% 可用
- 所有 P1 功能 100% 可用
- 用戶操作流程無變化
- 錯誤提示保持友好

### ✅ 性能表現
- API 調用響應時間 < 1秒
- UI 操作響應時間 < 2秒
- 大數據量加載 < 5秒
- 網絡異常自動恢復

### ✅ 安全性提升
- 客戶端無敏感密鑰
- Session Token 自動過期
- 權限檢查正常工作
- 錯誤信息不洩露敏感數據

### ✅ 可維護性
- 代碼結構清晰
- 錯誤處理統一
- 日誌記錄完整
- 配置管理簡化

這個適配方案確保了在提升安全性的同時，保持用戶體驗的完全一致性，並為未來的多客戶端支持奠定了堅實的基礎。所有現有的業務邏輯和 RPC 函數都會被完整保留，只是調用方式更加安全和標準化。