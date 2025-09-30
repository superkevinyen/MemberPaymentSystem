from supabase import create_client, Client
from typing import Any, Dict, List, Optional
import logging
from .settings import settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase 客戶端封裝類"""
    
    def __init__(self):
        self.url = settings.database.url
        self.service_role_key = settings.database.service_role_key
        self.anon_key = settings.database.anon_key
        self.client: Optional[Client] = None
        self.auth_session = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化 Supabase 客戶端"""
        try:
            # 使用 anon_key 創建客戶端（訪問 public schema）
            self.client = create_client(self.url, self.anon_key)
            logger.info("Supabase 客戶端初始化成功")
        except Exception as e:
            logger.error(f"Supabase 客戶端初始化失敗: {e}")
            raise Exception(f"無法連接到 Supabase: {e}")
    
    def rpc(self, function_name: str, params: Dict[str, Any]) -> Any:
        """調用 RPC 函數"""
        if not self.client:
            raise Exception("Supabase 客戶端未初始化")
        
        try:
            logger.debug(f"調用 RPC: {function_name}, 參數: {params}")
            response = self.client.rpc(function_name, params).execute()
            
            # 檢查響應
            if hasattr(response, 'data'):
                logger.debug(f"RPC 調用成功: {function_name}")
                return response.data
            else:
                logger.warning(f"RPC 響應格式異常: {function_name}")
                return response
                
        except Exception as e:
            logger.error(f"RPC 調用失敗: {function_name}, 錯誤: {e}")
            raise Exception(f"RPC 調用失敗: {e}")
    
    def query(self, table: str):
        """查詢表格數據"""
        if not self.client:
            raise Exception("Supabase 客戶端未初始化")
        
        try:
            # 直接查詢 public schema 中的表
            return self.client.table(table)
        except Exception as e:
            logger.error(f"查詢表格失敗: {table}, 錯誤: {e}")
            raise Exception(f"查詢表格失敗: {e}")
    
    def select(self, table: str, columns: str = "*", 
               filters: Optional[Dict[str, Any]] = None,
               limit: Optional[int] = None,
               offset: Optional[int] = None) -> List[Dict]:
        """簡化的查詢方法"""
        try:
            query = self.query(table).select(columns)
            
            # 應用過濾條件
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            # 應用分頁
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            response = query.execute()
            return getattr(response, 'data', [])
            
        except Exception as e:
            logger.error(f"查詢失敗: {table}, 錯誤: {e}")
            raise Exception(f"查詢失敗: {e}")
    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict:
        """插入數據"""
        try:
            response = self.query(table).insert(data).execute()
            return getattr(response, 'data', {})[0] if getattr(response, 'data', []) else {}
        except Exception as e:
            logger.error(f"插入數據失敗: {table}, 錯誤: {e}")
            raise Exception(f"插入數據失敗: {e}")
    
    def update(self, table: str, data: Dict[str, Any], 
               filters: Dict[str, Any]) -> List[Dict]:
        """更新數據"""
        try:
            query = self.query(table)
            
            # 應用過濾條件
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.update(data).execute()
            return getattr(response, 'data', [])
            
        except Exception as e:
            logger.error(f"更新數據失敗: {table}, 錯誤: {e}")
            raise Exception(f"更新數據失敗: {e}")
    
    def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict]:
        """刪除數據"""
        try:
            query = self.query(table)
            
            # 應用過濾條件
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = query.delete().execute()
            return getattr(response, 'data', [])
            
        except Exception as e:
            logger.error(f"刪除數據失敗: {table}, 錯誤: {e}")
            raise Exception(f"刪除數據失敗: {e}")
    
    def test_connection(self) -> bool:
        """測試連接"""
        try:
            # 使用 RPC 函數測試連接
            result = self.rpc("test_connection", {})
            if result and result.get('status') == 'success':
                logger.info("Supabase 連接測試成功")
                return True
            else:
                logger.error("Supabase 連接測試失敗: 無效的響應")
                return False
        except Exception as e:
            logger.error(f"Supabase 連接測試失敗: {e}")
            return False
    
    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        """使用 email 和密碼登入 (Supabase Auth)"""
        if not self.client:
            raise Exception("Supabase client not initialized")
        
        try:
            logger.debug(f"Attempting login: {email}")
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.session:
                self.auth_session = response.session
                logger.info(f"Login successful: {email}")
                return {
                    "user": response.user,
                    "session": response.session
                }
            else:
                raise Exception("Login failed: Invalid credentials")
                
        except Exception as e:
            logger.error(f"Login failed: {email}, error: {e}")
            raise Exception(f"Login failed: {e}")
    
    def sign_out(self):
        """登出"""
        if not self.client:
            return
        
        try:
            self.client.auth.sign_out()
            self.auth_session = None
            logger.info("Logout successful")
        except Exception as e:
            logger.error(f"Logout failed: {e}")
    
    def get_current_user(self) -> Optional[Dict]:
        """取得當前登入用戶"""
        if not self.client:
            return None
        
        try:
            response = self.client.auth.get_user()
            return response.user if response else None
        except Exception as e:
            logger.error(f"Get user failed: {e}")
            return None
    
    def is_authenticated(self) -> bool:
        """檢查是否已登入"""
        return self.auth_session is not None

# 全局 Supabase 客戶端實例
supabase_client = SupabaseClient()